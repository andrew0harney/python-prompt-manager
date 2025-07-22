"""Exception hierarchy for python-prompt-manager.

This module defines all custom exceptions used throughout the package,
following a clear hierarchy for better error handling and debugging.
"""


class PromptManagerError(Exception):
    """Base exception for all prompt manager errors."""

    pass


class ConfigurationError(PromptManagerError):
    """Raised when configuration is invalid or missing."""

    pass


class ValidationError(PromptManagerError):
    """Raised when validation fails."""

    pass


class SourceError(PromptManagerError):
    """Base exception for prompt source errors."""

    pass


class SourceNotFoundError(SourceError):
    """Raised when a prompt source is not found or misconfigured."""

    pass


class SourceConnectionError(SourceError):
    """Raised when unable to connect to a prompt source."""

    pass


class PromptError(PromptManagerError):
    """Base exception for prompt-related errors."""

    pass


class PromptNotFoundError(PromptError):
    """Raised when a prompt cannot be found."""

    def __init__(self, prompt_name: str, source: str = None, details: str = None):
        self.prompt_name = prompt_name
        self.source = source
        message = f"Prompt '{prompt_name}' not found"
        if source:
            message += f" in source '{source}'"
        if details:
            message += f": {details}"
        super().__init__(message)


class PromptRetrievalError(PromptError):
    """Raised when prompt retrieval fails."""

    def __init__(self, prompt_name: str, source: str, original_error: Exception):
        self.prompt_name = prompt_name
        self.source = source
        self.original_error = original_error
        message = f"Failed to retrieve prompt '{prompt_name}' from source '{source}': {str(original_error)}"
        super().__init__(message)


class RegistryError(PromptManagerError):
    """Base exception for registry-related errors."""

    pass


class PromptAlreadyRegisteredError(RegistryError):
    """Raised when attempting to register a prompt that already exists."""

    def __init__(self, prompt_name: str):
        self.prompt_name = prompt_name
        super().__init__(f"Prompt '{prompt_name}' is already registered")


class PromptNotRegisteredError(RegistryError):
    """Raised when attempting to access an unregistered prompt."""

    def __init__(self, prompt_name: str):
        self.prompt_name = prompt_name
        super().__init__(f"Prompt '{prompt_name}' is not registered")


# OpenAI-specific exceptions
class OpenAIError(SourceError):
    """Base exception for OpenAI-related errors."""

    pass


class OpenAIConfigError(OpenAIError, ConfigurationError):
    """Raised when OpenAI configuration is invalid."""

    pass


class OpenAIRateLimitError(OpenAIError):
    """Raised when OpenAI rate limit is exceeded."""

    pass


class OpenAITimeoutError(OpenAIError):
    """Raised when OpenAI request times out."""

    pass


# Local file source exceptions
class LocalSourceError(SourceError):
    """Base exception for local file source errors."""

    pass


class FileNotFoundError(LocalSourceError):
    """Raised when a prompt file is not found."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"Prompt file not found: {file_path}")


class FileReadError(LocalSourceError):
    """Raised when unable to read a prompt file."""

    def __init__(self, file_path: str, original_error: Exception):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(
            f"Failed to read prompt file '{file_path}': {str(original_error)}"
        )
