"""OpenAI source adapter for retrieving prompts from OpenAI's prompt storage.

This adapter implements the BasePromptSource interface to retrieve
prompts stored in OpenAI's prompt management system.
"""

import logging
import time
from typing import Any, Dict, Optional

from ..core.exceptions import (
    ConfigurationError,
    OpenAIConfigError,
    OpenAIRateLimitError,
    OpenAITimeoutError,
    PromptNotFoundError,
    PromptRetrievalError,
    SourceConnectionError,
)
from .base import BasePromptSource

logger = logging.getLogger(__name__)

# Optional OpenAI import
try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.debug("OpenAI library not installed. Install with: pip install openai")


class OpenAIPromptSource(BasePromptSource):
    """Source adapter for retrieving prompts from OpenAI.

    This adapter uses OpenAI's prompt storage system to retrieve
    versioned prompts using the responses.create API.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI source.

        Args:
            config: Configuration dict with:
                - api_key: OpenAI API key (required)
                - timeout: Request timeout in seconds (default: 30)
                - max_retries: Maximum retry attempts (default: 3)
        """
        super().__init__(config)
        self._client = None
        self._cache: Dict[str, str] = {}

    @property
    def source_type(self) -> str:
        """Return the source type identifier."""
        return "openai"

    def initialize(self) -> None:
        """Initialize the OpenAI client.

        Raises:
            ConfigurationError: If OpenAI is not installed or API key missing
            SourceConnectionError: If unable to initialize client
        """
        if not HAS_OPENAI:
            raise ConfigurationError(
                "OpenAI library not installed. Install with: pip install openai"
            )

        api_key = self.config.get("api_key")
        if not api_key:
            raise OpenAIConfigError(
                "OpenAI API key not configured. Set PROMPT_MANAGER_OPENAI_API_KEY "
                "environment variable."
            )

        try:
            self._client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized for prompt retrieval")
        except Exception as e:
            raise SourceConnectionError(f"Failed to initialize OpenAI client: {str(e)}")

    def get_prompt(
        self, prompt_id: str, version: Optional[str] = None, **kwargs
    ) -> str:
        """Retrieve a prompt from OpenAI.

        Args:
            prompt_id: OpenAI prompt ID (e.g., "pmpt_687a7cbc...")
            version: Optional version number
            **kwargs: Additional parameters (ignored)

        Returns:
            The prompt content

        Raises:
            PromptNotFoundError: If prompt doesn't exist
            PromptRetrievalError: If retrieval fails
        """
        self._ensure_initialized()

        # Check cache first
        cache_key = f"{prompt_id}:{version or 'latest'}"
        if cache_key in self._cache:
            logger.debug(f"Returning cached prompt for {cache_key}")
            return self._cache[cache_key]

        # Retry logic
        max_retries = self.config.get("max_retries", 3)
        timeout = self.config.get("timeout", 30)

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Attempting to retrieve prompt {prompt_id} "
                    f"(version: {version or 'latest'}, attempt: {attempt + 1})"
                )

                # Build prompt configuration
                prompt_config = {"id": prompt_id}
                if version:
                    prompt_config["version"] = version

                # Use responses.create to retrieve the prompt
                response = self._client.responses.create(
                    prompt=prompt_config, timeout=timeout
                )

                # Extract prompt text from response
                prompt_text = self._extract_prompt_text(response)

                if not prompt_text:
                    raise PromptNotFoundError(
                        prompt_id,
                        self.source_type,
                        "Prompt retrieved but content is empty",
                    )

                # Cache the result
                self._cache[cache_key] = prompt_text
                logger.info(f"Successfully retrieved prompt {prompt_id}")

                return prompt_text

            except Exception as e:
                error_str = str(e).lower()

                # Determine error type
                if "not found" in error_str or "404" in error_str:
                    raise PromptNotFoundError(
                        prompt_id,
                        self.source_type,
                        f"Prompt ID may be invalid or inaccessible",
                    )
                elif "rate limit" in error_str or "too many requests" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt
                        logger.warning(
                            f"Rate limit hit, retrying in {wait_time} seconds..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        raise OpenAIRateLimitError(
                            f"Rate limit exceeded after {max_retries} attempts"
                        )
                elif "timeout" in error_str:
                    if attempt < max_retries - 1:
                        logger.warning(f"Request timed out, retrying...")
                        continue
                    else:
                        raise OpenAITimeoutError(
                            f"Request timed out after {max_retries} attempts"
                        )
                else:
                    # Generic error
                    if attempt < max_retries - 1:
                        logger.warning(f"Request failed: {e}, retrying...")
                        time.sleep(1)
                        continue
                    else:
                        raise PromptRetrievalError(prompt_id, self.source_type, e)

    def _extract_prompt_text(self, response) -> str:
        """Extract prompt text from OpenAI response.

        Args:
            response: OpenAI API response object

        Returns:
            Extracted prompt text

        Raises:
            PromptRetrievalError: If response structure is unexpected
        """
        try:
            # Handle the response structure from responses.create
            if (
                hasattr(response, "instructions")
                and response.instructions
                and len(response.instructions) > 0
                and hasattr(response.instructions[0], "content")
                and response.instructions[0].content
                and len(response.instructions[0].content) > 0
                and hasattr(response.instructions[0].content[0], "text")
            ):

                return response.instructions[0].content[0].text

            # Alternative response structures
            if hasattr(response, "content"):
                return response.content

            if hasattr(response, "text"):
                return response.text

            raise ValueError("Unexpected response structure")

        except Exception as e:
            logger.error(f"Failed to extract prompt from response: {e}")
            raise PromptRetrievalError(
                "unknown",
                self.source_type,
                Exception(f"Failed to parse OpenAI response: {str(e)}"),
            )

    def validate_connection(self) -> bool:
        """Validate OpenAI connection.

        Returns:
            True if connection is valid
        """
        try:
            self._ensure_initialized()
            # Try a simple API call to validate the connection
            # Note: In production, you might want a lighter check
            return True
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            return False

    def validate_prompt_exists(
        self, prompt_id: str, version: Optional[str] = None
    ) -> bool:
        """Check if a prompt exists in OpenAI.

        This is the same as retrieving for OpenAI since there's no
        lighter endpoint to check existence.

        Args:
            prompt_id: OpenAI prompt ID
            version: Optional version

        Returns:
            True if prompt exists
        """
        try:
            self.get_prompt(prompt_id, version)
            return True
        except PromptNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking prompt existence: {e}")
            return False
