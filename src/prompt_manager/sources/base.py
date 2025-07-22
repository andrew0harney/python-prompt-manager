"""Base interface for prompt sources.

This module defines the abstract base class that all prompt sources must implement.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BasePromptSource(ABC):
    """Abstract base class for all prompt sources.

    All prompt sources must implement this interface to be used
    by the PromptManager.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the source with configuration.

        Args:
            config: Source-specific configuration dictionary
        """
        self.config = config
        self._initialized = False

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the source (e.g., establish connections).

        This method is called once when the source is first used.
        It should perform any necessary setup like establishing
        connections or validating configuration.

        Raises:
            SourceConnectionError: If initialization fails
            ConfigurationError: If configuration is invalid
        """
        pass

    @abstractmethod
    def get_prompt(
        self, prompt_id: str, version: Optional[str] = None, **kwargs
    ) -> str:
        """Retrieve a prompt by ID.

        Args:
            prompt_id: The prompt identifier
            version: Optional version specifier
            **kwargs: Additional source-specific parameters

        Returns:
            The prompt content as a string

        Raises:
            PromptNotFoundError: If the prompt doesn't exist
            PromptRetrievalError: If retrieval fails for other reasons
            SourceConnectionError: If source is not accessible
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """Validate that the source is accessible.

        This method should perform a lightweight check to ensure
        the source is reachable and properly configured.

        Returns:
            True if source is accessible, False otherwise
        """
        pass

    def validate_prompt_exists(
        self, prompt_id: str, version: Optional[str] = None
    ) -> bool:
        """Check if a prompt exists without retrieving it.

        Default implementation tries to retrieve the prompt.
        Sources can override for more efficient implementation.

        Args:
            prompt_id: The prompt identifier
            version: Optional version specifier

        Returns:
            True if prompt exists, False otherwise
        """
        try:
            self.get_prompt(prompt_id, version)
            return True
        except Exception:
            return False

    def _ensure_initialized(self) -> None:
        """Ensure the source is initialized before use."""
        if not self._initialized:
            logger.debug(f"Initializing {self.source_type} source")
            self.initialize()
            self._initialized = True

    def __repr__(self) -> str:
        """Return string representation of the source."""
        return f"{self.__class__.__name__}(type={self.source_type})"
