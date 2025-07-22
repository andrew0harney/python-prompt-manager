"""Core PromptManager implementation.

This module provides the main PromptManager class that coordinates
prompt retrieval from various sources with caching and validation.
"""

import logging
import time
from functools import lru_cache
from threading import RLock
from typing import Any, Dict, Optional, Type, Union

from ..sources.base import BasePromptSource
from ..sources.local import LocalFileSource
from ..sources.openai import OpenAIPromptSource
from .config import (
    PromptConfig,
    PromptManagerConfig,
    SourceType,
    ValidationMode,
    get_config,
    reset_config,
)
from .exceptions import (
    ConfigurationError,
    PromptManagerError,
    PromptNotRegisteredError,
    SourceNotFoundError,
    ValidationError,
)
from .registry import PromptRegistry

logger = logging.getLogger(__name__)


class PromptManager:
    """Main class for managing prompts from various sources.

    This class provides a unified interface for retrieving prompts
    from different sources (OpenAI, local files, etc.) with caching
    and validation support.

    Example:
        >>> pm = PromptManager()
        >>> prompt = pm.get_prompt("welcome_message")
        >>> prompt_with_vars = pm.get_prompt("greeting", variables={"name": "Alice"})
    """

    # Source type to class mapping
    SOURCE_CLASSES: Dict[SourceType, Type[BasePromptSource]] = {
        SourceType.OPENAI: OpenAIPromptSource,
        SourceType.LOCAL: LocalFileSource,
    }

    def __init__(
        self, config: Optional[Union[Dict[str, Any], PromptManagerConfig]] = None
    ):
        """Initialize the PromptManager.

        Args:
            config: Optional configuration - can be a dictionary or PromptManagerConfig.
                   If not provided, configuration is loaded from environment variables.
        """
        # Convert dict to PromptManagerConfig if needed
        if isinstance(config, dict):
            self.config = self._create_config_from_dict(config)
        else:
            self.config = config or get_config()

        self.registry = PromptRegistry()
        self._sources: Dict[SourceType, BasePromptSource] = {}
        self._cache: Dict[str, tuple[str, float]] = {}  # (content, timestamp)
        self._lock = RLock()

        # Register prompts from config
        self._register_configured_prompts()

        # Validate on startup if configured
        if self.config.validate_on_startup != ValidationMode.NONE:
            self.validate(self.config.validate_on_startup)

    def _create_config_from_dict(
        self, config_dict: Dict[str, Any]
    ) -> PromptManagerConfig:
        """Convert a dictionary configuration to PromptManagerConfig.

        Args:
            config_dict: Configuration dictionary as shown in README

        Returns:
            PromptManagerConfig instance
        """
        # Extract source configurations
        sources = config_dict.get("sources", {})
        openai_config = sources.get("openai", {})
        local_config = sources.get("local", {})

        # Convert prompts to PromptConfig objects
        prompts = {}
        for name, prompt_dict in config_dict.get("prompts", {}).items():
            # Build source_config based on the prompt source
            source_config = {}

            # For OpenAI prompts, 'id' maps to 'prompt_id'
            if prompt_dict.get("source") == "openai" and "id" in prompt_dict:
                source_config["prompt_id"] = prompt_dict["id"]

            # Add other fields to source_config
            for key in ["version", "path"]:
                if key in prompt_dict:
                    source_config[key] = prompt_dict[key]

            prompts[name] = PromptConfig(
                name=name,
                source=prompt_dict["source"],
                source_config=source_config,
                cache_ttl=prompt_dict.get("cache_ttl"),
            )

        # Handle validate_on_startup - convert boolean to ValidationMode
        validate_on_startup = config_dict.get("validate_on_startup", "env_only")
        if isinstance(validate_on_startup, bool):
            validate_on_startup = (
                ValidationMode.LOAD_TEST if validate_on_startup else ValidationMode.NONE
            )

        # Create the config
        return PromptManagerConfig(
            prompts=prompts,
            openai_api_key=openai_config.get("api_key"),
            openai_timeout=openai_config.get("timeout", 30),
            openai_max_retries=openai_config.get("max_retries", 3),
            prompts_dir=local_config.get("base_dir"),
            cache_ttl=config_dict.get("cache_ttl", 3600),
            cache_enabled=config_dict.get("cache_enabled", True),
            validate_on_startup=validate_on_startup,
            default_source=config_dict.get("default_source"),
        )

    def _register_configured_prompts(self) -> None:
        """Register prompts from configuration."""
        for name, prompt_config in self.config.prompts.items():
            self.registry.register(prompt_config)

        if self.config.prompts:
            logger.info(
                f"Registered {len(self.config.prompts)} prompts from configuration"
            )

    def get_prompt(
        self,
        name: str,
        version: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        default: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Retrieve a prompt by name.

        Args:
            name: The prompt name/identifier
            version: Optional version specifier
            variables: Variables for template substitution
            default: Default value if prompt not found
            **kwargs: Additional source-specific parameters

        Returns:
            The prompt content

        Raises:
            PromptNotRegisteredError: If prompt not registered and no default
            PromptRetrievalError: If retrieval fails
        """
        try:
            # Check cache first
            cache_key = f"{name}:{version or 'latest'}"
            cached_content = self._get_cached(cache_key)
            if cached_content is not None:
                return self._apply_variables(cached_content, variables)

            # Get prompt configuration
            try:
                prompt_config = self.registry.get(name)
            except PromptNotRegisteredError:
                if default is not None:
                    return self._apply_variables(default, variables)
                raise

            # Get the source
            source = self._get_source(prompt_config.source)

            # Prepare retrieval parameters
            retrieval_params = prompt_config.source_config.copy()
            if version:
                retrieval_params["version"] = version
            if variables:
                retrieval_params["variables"] = variables
            retrieval_params.update(kwargs)

            # Retrieve the prompt
            prompt_id = retrieval_params.pop("prompt_id", name)
            content = source.get_prompt(prompt_id, **retrieval_params)

            # Cache the result
            if self.config.cache_enabled:
                ttl = prompt_config.cache_ttl or self.config.cache_ttl
                self._cache_prompt(cache_key, content, ttl)

            return self._apply_variables(content, variables)

        except Exception as e:
            logger.error(f"Failed to get prompt '{name}': {e}")
            if default is not None:
                logger.info(f"Using default value for prompt '{name}'")
                return self._apply_variables(default, variables)
            raise

    def get(self, name: str, **kwargs) -> str:
        """Alias for get_prompt() to match the simpler API shown in examples.

        Args:
            name: Prompt name
            **kwargs: Same as get_prompt (version, variables, default, etc.)

        Returns:
            The prompt content
        """
        return self.get_prompt(name, **kwargs)

    def register_prompt(
        self,
        name: str,
        source: str,
        source_config: Optional[Dict] = None,
        cache_ttl: Optional[int] = None,
        overwrite: bool = False,
    ) -> None:
        """Register a prompt programmatically.

        Args:
            name: Prompt name/identifier
            source: Source type (e.g., "openai", "local")
            source_config: Source-specific configuration
            cache_ttl: Cache TTL override
            overwrite: Whether to overwrite existing registration

        Raises:
            ConfigurationError: If configuration is invalid
            PromptAlreadyRegisteredError: If exists and overwrite=False
        """
        self.registry.register_from_dict(
            name=name,
            source=source,
            source_config=source_config,
            cache_ttl=cache_ttl,
            overwrite=overwrite,
        )
        logger.info(f"Registered prompt '{name}' with source '{source}'")

    def validate(self, mode: Optional[ValidationMode] = None) -> None:
        """Validate prompt manager configuration and prompts.

        Args:
            mode: Validation mode (overrides config default)

        Raises:
            ValidationError: If validation fails
        """
        mode = mode or self.config.validate_on_startup

        logger.info(f"Validating prompt manager (mode: {mode.value})")

        # Always validate configuration
        self.config.validate(mode)

        # Validate registry
        registry_errors = self.registry.validate_prompts()
        if registry_errors:
            raise ValidationError(
                "Prompt registry validation failed:\n"
                + "\n".join(f"  - {e}" for e in registry_errors)
            )

        # If load test mode, try to load all prompts
        if mode == ValidationMode.LOAD_TEST:
            self._validate_prompt_loading()

        logger.info("Validation completed successfully")

    def _validate_prompt_loading(self) -> None:
        """Validate that all registered prompts can be loaded."""
        errors = []

        for name in self.registry.list_prompts():
            try:
                prompt_config = self.registry.get(name)
                source = self._get_source(prompt_config.source)

                # Check if prompt exists
                prompt_id = prompt_config.source_config.get("prompt_id", name)
                version = prompt_config.source_config.get("version")

                if not source.validate_prompt_exists(prompt_id, version):
                    errors.append(
                        f"Prompt '{name}' not found in {prompt_config.source.value} source"
                    )

            except Exception as e:
                errors.append(f"Failed to validate prompt '{name}': {str(e)}")

        if errors:
            raise ValidationError(
                "Prompt loading validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    def _get_source(self, source_type: SourceType) -> BasePromptSource:
        """Get or create a source instance.

        Args:
            source_type: The source type

        Returns:
            The source instance

        Raises:
            SourceNotFoundError: If source type not supported
            SourceConnectionError: If source initialization fails
        """
        with self._lock:
            if source_type not in self._sources:
                # Get source class
                source_class = self.SOURCE_CLASSES.get(source_type)
                if not source_class:
                    raise SourceNotFoundError(
                        f"Unsupported source type: {source_type.value}"
                    )

                # Prepare source configuration
                source_config = self._get_source_config(source_type)

                # Create and initialize source
                source = source_class(source_config)
                self._sources[source_type] = source

                logger.debug(f"Created {source_type.value} source")

            return self._sources[source_type]

    def _get_source_config(self, source_type: SourceType) -> Dict[str, Any]:
        """Get configuration for a specific source type.

        Args:
            source_type: The source type

        Returns:
            Source-specific configuration dictionary
        """
        if source_type == SourceType.OPENAI:
            return {
                "api_key": self.config.openai_api_key,
                "timeout": self.config.openai_timeout,
                "max_retries": self.config.openai_max_retries,
            }
        elif source_type == SourceType.LOCAL:
            return {
                "base_dir": self.config.prompts_dir,
                "encoding": "utf-8",
                "auto_reload": False,  # Could be configurable
            }
        else:
            return {}

    def _get_cached(self, cache_key: str) -> Optional[str]:
        """Get prompt from cache if valid.

        Args:
            cache_key: The cache key

        Returns:
            Cached content or None if not found/expired
        """
        if not self.config.cache_enabled:
            return None

        with self._lock:
            if cache_key in self._cache:
                content, timestamp = self._cache[cache_key]

                # Check if expired (0 means no expiry)
                if self.config.cache_ttl > 0:
                    if time.time() - timestamp > self.config.cache_ttl:
                        del self._cache[cache_key]
                        return None

                logger.debug(f"Cache hit for {cache_key}")
                return content

        return None

    def _cache_prompt(self, cache_key: str, content: str, ttl: int) -> None:
        """Cache a prompt.

        Args:
            cache_key: The cache key
            content: The prompt content
            ttl: Time to live in seconds
        """
        if not self.config.cache_enabled or ttl == 0:
            return

        with self._lock:
            self._cache[cache_key] = (content, time.time())
            logger.debug(f"Cached prompt {cache_key} with TTL {ttl}s")

    def _apply_variables(
        self, content: str, variables: Optional[Dict[str, Any]]
    ) -> str:
        """Apply variable substitution to content.

        Args:
            content: The content with placeholders
            variables: Variable values

        Returns:
            Content with substituted variables
        """
        if not variables:
            return content

        try:
            return content.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable for substitution: {e}")
            return content

    def clear_cache(self) -> None:
        """Clear all cached prompts."""
        with self._lock:
            self._cache.clear()
            logger.info("Cleared prompt cache")

    def list_prompts(self) -> list[str]:
        """Get list of all registered prompt names.

        Returns:
            List of prompt names
        """
        return self.registry.list_prompts()

    def prompt_exists(self, name: str) -> bool:
        """Check if a prompt is registered.

        Args:
            name: Prompt name

        Returns:
            True if registered
        """
        return self.registry.exists(name)

    def __repr__(self) -> str:
        """String representation of the PromptManager."""
        return (
            f"PromptManager("
            f"prompts={len(self.registry)}, "
            f"sources={sorted(s.value for s in self.registry.get_sources_in_use())}, "
            f"cache_enabled={self.config.cache_enabled})"
        )


# Global instance for convenience
_global_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get the global PromptManager instance.

    Creates the instance on first call.

    Returns:
        The global PromptManager instance
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = PromptManager()
    return _global_manager


def reset_prompt_manager() -> None:
    """Reset the global PromptManager instance.

    Useful for testing or reconfiguration.
    """
    global _global_manager
    _global_manager = None
    reset_config()


# Convenience function for simple usage
def get_prompt(name: str, **kwargs) -> str:
    """Get a prompt using the global PromptManager.

    Convenience function for simple use cases.

    Args:
        name: Prompt name
        **kwargs: Additional parameters passed to get_prompt

    Returns:
        The prompt content
    """
    return get_prompt_manager().get_prompt(name, **kwargs)
