"""Local file source adapter for retrieving prompts from the filesystem.

This adapter implements the BasePromptSource interface to retrieve
prompts stored as files on the local filesystem.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from ..core.exceptions import (
    ConfigurationError,
)
from ..core.exceptions import FileNotFoundError as PromptFileNotFoundError
from ..core.exceptions import (
    FileReadError,
    PromptNotFoundError,
    PromptRetrievalError,
    SourceConnectionError,
)
from .base import BasePromptSource

logger = logging.getLogger(__name__)

# Optional YAML support
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    logger.debug("PyYAML not installed. Install with: pip install pyyaml")


class LocalFileSource(BasePromptSource):
    """Source adapter for retrieving prompts from local files.

    This adapter reads prompts from files on the local filesystem.
    Supports plain text, JSON, and YAML formats.
    """

    SUPPORTED_EXTENSIONS = {".txt", ".text", ".json", ".yaml", ".yml"}

    def __init__(self, config: Dict[str, Any]):
        """Initialize local file source.

        Args:
            config: Configuration dict with:
                - base_dir: Base directory for prompts (optional)
                - encoding: File encoding (default: utf-8)
                - auto_reload: Watch files for changes (default: False)
        """
        super().__init__(config)
        self._base_dir = None
        self._encoding = config.get("encoding", "utf-8")
        self._auto_reload = config.get("auto_reload", False)
        self._cache: Dict[str, str] = {}
        self._file_mtimes: Dict[str, float] = {}

    @property
    def source_type(self) -> str:
        """Return the source type identifier."""
        return "local"

    def initialize(self) -> None:
        """Initialize the local file source.

        Validates that the base directory exists if configured.

        Raises:
            ConfigurationError: If base_dir is invalid
        """
        base_dir = self.config.get("base_dir")
        if base_dir:
            self._base_dir = Path(base_dir).expanduser().resolve()
            if not self._base_dir.exists():
                raise ConfigurationError(
                    f"Prompts directory does not exist: {self._base_dir}"
                )
            if not self._base_dir.is_dir():
                raise ConfigurationError(
                    f"Prompts path is not a directory: {self._base_dir}"
                )
            logger.info(
                f"Local file source initialized with base directory: {self._base_dir}"
            )
        else:
            logger.info("Local file source initialized without base directory")

    def get_prompt(
        self, prompt_id: str, version: Optional[str] = None, **kwargs
    ) -> str:
        """Retrieve a prompt from a local file.

        Args:
            prompt_id: File path (relative to base_dir or absolute)
            version: Version suffix (e.g., "v2" -> file.v2.txt)
            **kwargs: Additional parameters:
                - path: Override path (ignores prompt_id)
                - variables: Dict of variables for template substitution

        Returns:
            The prompt content

        Raises:
            PromptNotFoundError: If file doesn't exist
            PromptRetrievalError: If file read fails
        """
        self._ensure_initialized()

        # Determine file path
        file_path = self._resolve_file_path(prompt_id, version, kwargs.get("path"))

        # Check cache and file modification time
        if self._auto_reload and str(file_path) in self._cache:
            if self._is_file_modified(file_path):
                logger.debug(f"File {file_path} modified, reloading")
                del self._cache[str(file_path)]

        # Return cached content if available
        cache_key = str(file_path)
        if cache_key in self._cache and not self._auto_reload:
            logger.debug(f"Returning cached prompt from {file_path}")
            return self._cache[cache_key]

        # Read the file
        try:
            content = self._read_file(file_path)

            # Apply variable substitution if provided
            variables = kwargs.get("variables", {})
            if variables:
                content = self._substitute_variables(content, variables)

            # Cache the content
            self._cache[cache_key] = content
            if self._auto_reload:
                self._file_mtimes[cache_key] = file_path.stat().st_mtime

            logger.info(f"Successfully loaded prompt from {file_path}")
            return content

        except FileNotFoundError:
            raise PromptNotFoundError(
                prompt_id, self.source_type, f"File not found: {file_path}"
            )
        except Exception as e:
            raise PromptRetrievalError(prompt_id, self.source_type, e)

    def _resolve_file_path(
        self, prompt_id: str, version: Optional[str], override_path: Optional[str]
    ) -> Path:
        """Resolve the full file path for a prompt.

        Args:
            prompt_id: Base filename or path
            version: Optional version suffix
            override_path: Override path from kwargs

        Returns:
            Resolved Path object

        Raises:
            PromptNotFoundError: If no valid file found
        """
        # Use override path if provided
        if override_path:
            path = Path(override_path).expanduser()
            # If override path is relative and we have a base_dir, resolve relative to base_dir
            if not path.is_absolute() and self._base_dir:
                return (self._base_dir / path).resolve()
            return path.resolve()

        # Start with prompt_id as base
        base_path = Path(prompt_id)

        # If absolute path, use as-is
        if base_path.is_absolute():
            file_path = base_path.expanduser().resolve()
        else:
            # Relative to base_dir if configured
            if self._base_dir:
                file_path = (self._base_dir / base_path).resolve()
            else:
                file_path = base_path.resolve()

        # Handle version suffix
        if version:
            # Try version as part of filename (e.g., prompt.v2.txt)
            versioned_name = f"{file_path.stem}.{version}{file_path.suffix}"
            versioned_path = file_path.parent / versioned_name
            if versioned_path.exists():
                return versioned_path

            # Try version as subdirectory (e.g., v2/prompt.txt)
            version_dir = file_path.parent / version / file_path.name
            if version_dir.exists():
                return version_dir

        # Try to find file with supported extensions if no extension given
        if not file_path.suffix:
            for ext in self.SUPPORTED_EXTENSIONS:
                candidate = file_path.with_suffix(ext)
                if candidate.exists():
                    return candidate

        # Return the path as-is (existence check happens in caller)
        return file_path

    def _read_file(self, file_path: Path) -> str:
        """Read content from a file.

        Args:
            file_path: Path to the file

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
            FileReadError: If read fails
        """
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        try:
            with open(file_path, "r", encoding=self._encoding) as f:
                content = f.read()

            # Handle different file formats
            if file_path.suffix in {".json"}:
                # Validate JSON and extract prompt field if present
                data = json.loads(content)
                if isinstance(data, dict) and "prompt" in data:
                    return data["prompt"]
                elif isinstance(data, str):
                    return data
                else:
                    return json.dumps(data, indent=2)

            elif file_path.suffix in {".yaml", ".yml"}:
                if not HAS_YAML:
                    logger.warning(
                        f"YAML file {file_path} found but PyYAML not installed. "
                        "Reading as plain text."
                    )
                    return content

                # Validate YAML and extract prompt field if present
                data = yaml.safe_load(content)
                if isinstance(data, dict) and "prompt" in data:
                    return data["prompt"]
                elif isinstance(data, str):
                    return data
                else:
                    return yaml.dump(data)

            # Plain text
            return content.strip()

        except Exception as e:
            raise FileReadError(str(file_path), e)

    def _substitute_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in prompt content.

        Uses Python string formatting with {variable} syntax.

        Args:
            content: Prompt content with placeholders
            variables: Variable values

        Returns:
            Content with substituted variables
        """
        try:
            return content.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing variable for substitution: {e}")
            # Return content as-is if substitution fails
            return content

    def _is_file_modified(self, file_path: Path) -> bool:
        """Check if a file has been modified since last read.

        Args:
            file_path: Path to check

        Returns:
            True if modified or not tracked
        """
        cache_key = str(file_path)
        if cache_key not in self._file_mtimes:
            return True

        try:
            current_mtime = file_path.stat().st_mtime
            return current_mtime > self._file_mtimes[cache_key]
        except Exception:
            return True

    def validate_connection(self) -> bool:
        """Validate local file source.

        Returns:
            True if base directory exists (if configured)
        """
        try:
            self._ensure_initialized()
            if self._base_dir:
                return self._base_dir.exists() and self._base_dir.is_dir()
            return True
        except Exception as e:
            logger.error(f"Local file source validation failed: {e}")
            return False

    def validate_prompt_exists(
        self, prompt_id: str, version: Optional[str] = None
    ) -> bool:
        """Check if a prompt file exists.

        More efficient than retrieving for local files.

        Args:
            prompt_id: File identifier
            version: Optional version

        Returns:
            True if file exists
        """
        try:
            self._ensure_initialized()
            file_path = self._resolve_file_path(prompt_id, version, None)
            return file_path.exists() and file_path.is_file()
        except Exception:
            return False
