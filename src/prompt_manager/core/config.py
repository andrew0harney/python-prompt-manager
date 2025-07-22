"""Configuration management for prompt manager.

Handles environment-based configuration with sensible defaults
and validation.
"""

import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional, Set

try:
    from pydantic import BaseModel, Field, ValidationError, field_validator
except ImportError:
    # Fallback for minimal installation
    BaseModel = object
    Field = lambda *args, **kwargs: None
    ValidationError = Exception
    field_validator = lambda *args, **kwargs: lambda func: func

from .exceptions import ConfigurationError
from .exceptions import ValidationError as PromptValidationError

logger = logging.getLogger(__name__)


class SourceType(str, Enum):
    """Supported prompt source types."""

    OPENAI = "openai"
    LOCAL = "local"

    @classmethod
    def from_string(cls, value: str) -> "SourceType":
        """Convert string to SourceType, case-insensitive."""
        try:
            return cls(value.lower())
        except ValueError:
            valid_types = ", ".join([t.value for t in cls])
            raise ConfigurationError(
                f"Invalid source type '{value}'. Valid types are: {valid_types}"
            )


class ValidationMode(str, Enum):
    """Validation modes for prompt manager."""

    NONE = "none"  # No validation
    ENV_ONLY = "env_only"  # Only validate environment variables exist
    LOAD_TEST = "load_test"  # Actually try to load prompts (network calls)

    @classmethod
    def from_string(cls, value: str) -> "ValidationMode":
        """Convert string to ValidationMode, case-insensitive."""
        try:
            return cls(value.lower())
        except ValueError:
            valid_modes = ", ".join([m.value for m in cls])
            raise ConfigurationError(
                f"Invalid validation mode '{value}'. Valid modes are: {valid_modes}"
            )


class PromptConfig(BaseModel if BaseModel != object else object):
    """Configuration for a single prompt."""

    name: str = Field(..., description="Prompt name/identifier")
    source: SourceType = Field(..., description="Source type for this prompt")
    source_config: Dict[str, Any] = Field(
        default_factory=dict, description="Source-specific configuration"
    )
    cache_ttl: Optional[int] = Field(
        None, description="Cache TTL in seconds, None means use global default"
    )

    @field_validator("source", mode="before")
    def validate_source(cls, v):
        if isinstance(v, str):
            return SourceType.from_string(v)
        return v

    @classmethod
    def from_env(cls, name: str) -> Optional["PromptConfig"]:
        """Create PromptConfig from environment variables.

        Expected format:
        PROMPT_{NAME}_SOURCE=openai
        PROMPT_{NAME}_ID=pmpt_123...
        PROMPT_{NAME}_VERSION=1
        PROMPT_{NAME}_PATH=/path/to/prompt.txt
        PROMPT_{NAME}_CACHE_TTL=3600
        """
        env_prefix = f"PROMPT_{name.upper()}"
        source = os.getenv(f"{env_prefix}_SOURCE")

        if not source:
            return None

        # Build source-specific config
        source_config = {}

        # Common fields
        if prompt_id := os.getenv(f"{env_prefix}_ID"):
            source_config["prompt_id"] = prompt_id
        if version := os.getenv(f"{env_prefix}_VERSION"):
            source_config["version"] = version
        if path := os.getenv(f"{env_prefix}_PATH"):
            source_config["path"] = path

        # Cache TTL
        cache_ttl = None
        if ttl_str := os.getenv(f"{env_prefix}_CACHE_TTL"):
            try:
                cache_ttl = int(ttl_str)
            except ValueError:
                raise ConfigurationError(
                    f"Invalid cache TTL for prompt '{name}': {ttl_str}"
                )

        return cls(
            name=name, source=source, source_config=source_config, cache_ttl=cache_ttl
        )


class PromptManagerConfig(BaseModel if BaseModel != object else object):
    """Main configuration for PromptManager."""

    # Global settings
    default_source: Optional[SourceType] = Field(
        None, description="Default source type when not specified per-prompt"
    )
    cache_enabled: bool = Field(True, description="Enable prompt caching")
    cache_ttl: int = Field(3600, description="Default cache TTL in seconds")
    validate_on_startup: ValidationMode = Field(
        ValidationMode.ENV_ONLY, description="Validation mode on startup"
    )

    # Source configurations
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    openai_timeout: int = Field(30, description="OpenAI request timeout in seconds")
    openai_max_retries: int = Field(
        3, description="Maximum retries for OpenAI requests"
    )

    prompts_dir: Optional[str] = Field(
        None, description="Base directory for local prompt files"
    )

    # Registered prompts
    prompts: Dict[str, PromptConfig] = Field(
        default_factory=dict, description="Registered prompt configurations"
    )

    @field_validator("default_source", mode="before")
    def validate_default_source(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            return SourceType.from_string(v)
        return v

    @field_validator("validate_on_startup", mode="before")
    def validate_validation_mode(cls, v):
        if isinstance(v, str):
            return ValidationMode.from_string(v)
        return v

    @classmethod
    def from_env(cls) -> "PromptManagerConfig":
        """Create configuration from environment variables.

        Environment variable format:
        PROMPT_MANAGER_DEFAULT_SOURCE=openai
        PROMPT_MANAGER_CACHE_ENABLED=true
        PROMPT_MANAGER_CACHE_TTL=3600
        PROMPT_MANAGER_VALIDATE_ON_STARTUP=env_only
        PROMPT_MANAGER_OPENAI_API_KEY=sk-...
        PROMPT_MANAGER_OPENAI_TIMEOUT=30
        PROMPT_MANAGER_OPENAI_MAX_RETRIES=3
        PROMPT_MANAGER_PROMPTS_DIR=/app/prompts
        """
        # Parse basic settings
        config_dict = {
            "default_source": os.getenv("PROMPT_MANAGER_DEFAULT_SOURCE"),
            "cache_enabled": os.getenv("PROMPT_MANAGER_CACHE_ENABLED", "true").lower()
            == "true",
            "cache_ttl": int(os.getenv("PROMPT_MANAGER_CACHE_TTL", "3600")),
            "validate_on_startup": os.getenv(
                "PROMPT_MANAGER_VALIDATE_ON_STARTUP", "env_only"
            ),
            "openai_api_key": os.getenv("PROMPT_MANAGER_OPENAI_API_KEY"),
            "openai_timeout": int(os.getenv("PROMPT_MANAGER_OPENAI_TIMEOUT", "30")),
            "openai_max_retries": int(
                os.getenv("PROMPT_MANAGER_OPENAI_MAX_RETRIES", "3")
            ),
            "prompts_dir": os.getenv("PROMPT_MANAGER_PROMPTS_DIR"),
            "prompts": {},
        }

        # Auto-discover prompts from environment
        discovered_prompts = cls._discover_prompts_from_env()
        config_dict["prompts"] = discovered_prompts

        try:
            return cls(**config_dict)
        except (ValidationError, ValueError) as e:
            raise ConfigurationError(f"Invalid configuration: {str(e)}")

    @staticmethod
    def _discover_prompts_from_env() -> Dict[str, PromptConfig]:
        """Discover prompt configurations from environment variables."""
        prompts = {}
        seen_names: Set[str] = set()

        # Look for PROMPT_*_SOURCE variables
        for key in os.environ:
            if key.startswith("PROMPT_") and key.endswith("_SOURCE"):
                # Extract prompt name
                parts = key.split("_")
                if len(parts) >= 3:  # PROMPT_NAME_SOURCE
                    name = "_".join(parts[1:-1]).lower()
                    if name not in seen_names:
                        seen_names.add(name)
                        if config := PromptConfig.from_env(name):
                            prompts[name] = config
                            logger.debug(f"Discovered prompt '{name}' from environment")

        return prompts

    def validate_sources(self) -> List[str]:
        """Validate that required source configurations are present.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check if any source is configured
        has_openai = bool(self.openai_api_key)
        has_local = bool(self.prompts_dir)

        if not (has_openai or has_local):
            errors.append(
                "No prompt sources configured. Set either PROMPT_MANAGER_OPENAI_API_KEY "
                "or PROMPT_MANAGER_PROMPTS_DIR environment variables."
            )

        # Validate each prompt has required config
        for name, prompt_config in self.prompts.items():
            if prompt_config.source == SourceType.OPENAI:
                if not has_openai:
                    errors.append(
                        f"Prompt '{name}' uses OpenAI source but PROMPT_MANAGER_OPENAI_API_KEY is not set"
                    )
                if "prompt_id" not in prompt_config.source_config:
                    errors.append(
                        f"Prompt '{name}' uses OpenAI source but no prompt ID configured. "
                        f"Set PROMPT_{name.upper()}_ID environment variable."
                    )

            elif prompt_config.source == SourceType.LOCAL:
                if not has_local:
                    errors.append(
                        f"Prompt '{name}' uses local source but PROMPT_MANAGER_PROMPTS_DIR is not set"
                    )
                if "path" not in prompt_config.source_config:
                    errors.append(
                        f"Prompt '{name}' uses local source but no path configured. "
                        f"Set PROMPT_{name.upper()}_PATH environment variable."
                    )

        return errors

    def validate(self, mode: Optional[ValidationMode] = None) -> None:
        """Validate configuration based on validation mode.

        Args:
            mode: Override the default validation mode

        Raises:
            PromptValidationError: If validation fails
        """
        mode = mode or self.validate_on_startup

        if mode == ValidationMode.NONE:
            return

        # Always validate source configuration
        errors = self.validate_sources()

        if errors:
            raise PromptValidationError(
                "Configuration validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        logger.info(f"Configuration validated successfully (mode: {mode.value})")


# Global configuration instance
_config: Optional[PromptManagerConfig] = None


def get_config() -> PromptManagerConfig:
    """Get the global configuration instance, creating it if needed."""
    global _config
    if _config is None:
        _config = PromptManagerConfig.from_env()
    return _config


def reset_config() -> None:
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None
