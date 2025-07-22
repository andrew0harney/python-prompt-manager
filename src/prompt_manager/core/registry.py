"""Prompt registry for managing prompt configurations.

This module provides a registry system for managing prompt configurations,
including registration, retrieval, and validation.
"""

import logging
from threading import RLock
from typing import Dict, List, Optional, Set

from .config import PromptConfig, SourceType
from .exceptions import (
    ConfigurationError,
    PromptAlreadyRegisteredError,
    PromptNotRegisteredError,
)

logger = logging.getLogger(__name__)


class PromptRegistry:
    """Registry for managing prompt configurations.

    Thread-safe registry for storing and retrieving prompt configurations.
    """

    def __init__(self):
        """Initialize the registry."""
        self._prompts: Dict[str, PromptConfig] = {}
        self._lock = RLock()
        self._sources_in_use: Set[SourceType] = set()

    def register(self, prompt_config: PromptConfig, overwrite: bool = False) -> None:
        """Register a prompt configuration.

        Args:
            prompt_config: The prompt configuration to register
            overwrite: Whether to overwrite existing registration

        Raises:
            PromptAlreadyRegisteredError: If prompt exists and overwrite=False
        """
        with self._lock:
            if prompt_config.name in self._prompts and not overwrite:
                raise PromptAlreadyRegisteredError(prompt_config.name)

            self._prompts[prompt_config.name] = prompt_config
            self._sources_in_use.add(prompt_config.source)

            logger.debug(
                f"Registered prompt '{prompt_config.name}' "
                f"with source '{prompt_config.source.value}'"
            )

    def register_from_dict(
        self,
        name: str,
        source: str,
        source_config: Optional[Dict] = None,
        cache_ttl: Optional[int] = None,
        overwrite: bool = False,
    ) -> None:
        """Register a prompt from dictionary values.

        Convenience method for registering without creating PromptConfig.

        Args:
            name: Prompt name
            source: Source type (string)
            source_config: Source-specific configuration
            cache_ttl: Cache TTL override
            overwrite: Whether to overwrite existing

        Raises:
            ConfigurationError: If configuration is invalid
            PromptAlreadyRegisteredError: If exists and overwrite=False
        """
        try:
            config = PromptConfig(
                name=name,
                source=source,
                source_config=source_config or {},
                cache_ttl=cache_ttl,
            )
            self.register(config, overwrite)
        except Exception as e:
            raise ConfigurationError(f"Failed to register prompt '{name}': {str(e)}")

    def get(self, name: str) -> PromptConfig:
        """Get a prompt configuration by name.

        Args:
            name: Prompt name

        Returns:
            The prompt configuration

        Raises:
            PromptNotRegisteredError: If prompt not found
        """
        with self._lock:
            if name not in self._prompts:
                raise PromptNotRegisteredError(name)
            return self._prompts[name]

    def exists(self, name: str) -> bool:
        """Check if a prompt is registered.

        Args:
            name: Prompt name

        Returns:
            True if registered
        """
        with self._lock:
            return name in self._prompts

    def list_prompts(self) -> List[str]:
        """Get list of all registered prompt names.

        Returns:
            List of prompt names
        """
        with self._lock:
            return list(self._prompts.keys())

    def get_all(self) -> Dict[str, PromptConfig]:
        """Get all registered prompt configurations.

        Returns:
            Dictionary of name -> PromptConfig
        """
        with self._lock:
            return self._prompts.copy()

    def remove(self, name: str) -> None:
        """Remove a prompt from the registry.

        Args:
            name: Prompt name to remove

        Raises:
            PromptNotRegisteredError: If prompt not found
        """
        with self._lock:
            if name not in self._prompts:
                raise PromptNotRegisteredError(name)

            config = self._prompts.pop(name)

            # Update sources in use
            self._update_sources_in_use()

            logger.debug(f"Removed prompt '{name}' from registry")

    def clear(self) -> None:
        """Clear all registered prompts."""
        with self._lock:
            self._prompts.clear()
            self._sources_in_use.clear()
            logger.debug("Cleared all prompts from registry")

    def get_sources_in_use(self) -> Set[SourceType]:
        """Get set of source types currently in use.

        Returns:
            Set of SourceType values
        """
        with self._lock:
            return self._sources_in_use.copy()

    def _update_sources_in_use(self) -> None:
        """Update the set of sources in use."""
        self._sources_in_use = {config.source for config in self._prompts.values()}

    def validate_prompts(self, source_type: Optional[SourceType] = None) -> List[str]:
        """Validate registered prompts have required configuration.

        Args:
            source_type: Only validate prompts for this source type

        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []

        with self._lock:
            for name, config in self._prompts.items():
                # Skip if filtering by source type
                if source_type and config.source != source_type:
                    continue

                # Source-specific validation
                if config.source == SourceType.OPENAI:
                    if "prompt_id" not in config.source_config:
                        errors.append(
                            f"Prompt '{name}': OpenAI source requires 'prompt_id' "
                            "in source configuration"
                        )

                elif config.source == SourceType.LOCAL:
                    # Local prompts need either a path or will use the name as path
                    # No required fields, but we could validate path exists
                    pass

        return errors

    def __len__(self) -> int:
        """Get number of registered prompts."""
        with self._lock:
            return len(self._prompts)

    def __contains__(self, name: str) -> bool:
        """Check if prompt is registered using 'in' operator."""
        return self.exists(name)

    def __repr__(self) -> str:
        """String representation of the registry."""
        with self._lock:
            return (
                f"PromptRegistry("
                f"prompts={len(self._prompts)}, "
                f"sources={sorted(s.value for s in self._sources_in_use)})"
            )
