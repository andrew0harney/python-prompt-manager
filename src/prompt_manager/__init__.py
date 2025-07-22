"""Python Prompt Manager - Centralized prompt management for LLM applications.

A lightweight library for managing prompts across different storage backends,
with built-in caching and environment-based configuration.

Basic usage:
    from prompt_manager import get_prompt

    # Get a prompt by name
    prompt = get_prompt("welcome_message")

    # With template variables
    prompt = get_prompt("greeting", variables={"name": "Alice"})
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.config import (
    PromptConfig,
    PromptManagerConfig,
    SourceType,
    ValidationMode,
    get_config,
    reset_config,
)

# Exception imports
from .core.exceptions import (
    ConfigurationError,
    PromptError,
    PromptManagerError,
    PromptNotFoundError,
    PromptNotRegisteredError,
    PromptRetrievalError,
    SourceError,
    ValidationError,
)

# Core imports
from .core.manager import (
    PromptManager,
    get_prompt,
    get_prompt_manager,
    reset_prompt_manager,
)
from .core.registry import PromptRegistry

# Source imports
from .sources.base import BasePromptSource

__all__ = [
    # Core functionality
    "PromptManager",
    "get_prompt_manager",
    "reset_prompt_manager",
    "get_prompt",
    # Configuration
    "PromptConfig",
    "PromptManagerConfig",
    "SourceType",
    "ValidationMode",
    "get_config",
    "reset_config",
    # Registry
    "PromptRegistry",
    # Exceptions
    "PromptManagerError",
    "ConfigurationError",
    "ValidationError",
    "SourceError",
    "PromptError",
    "PromptNotFoundError",
    "PromptRetrievalError",
    "PromptNotRegisteredError",
    # Base classes
    "BasePromptSource",
]
