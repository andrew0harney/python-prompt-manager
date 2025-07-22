"""Tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from prompt_manager.core.config import (
    PromptConfig,
    PromptManagerConfig,
    SourceType,
    ValidationMode,
    get_config,
    reset_config,
)
from prompt_manager.core.exceptions import ConfigurationError


class TestPromptConfig:
    """Test PromptConfig functionality."""

    def test_prompt_config_creation(self):
        """Test creating a prompt configuration."""
        config = PromptConfig(
            name="test_prompt",
            source=SourceType.OPENAI,
            source_config={"prompt_id": "pmpt_123"},
            cache_ttl=3600,
        )

        assert config.name == "test_prompt"
        assert config.source == SourceType.OPENAI
        assert config.source_config["prompt_id"] == "pmpt_123"
        assert config.cache_ttl == 3600

    def test_prompt_config_from_env(self):
        """Test creating prompt config from environment variables."""
        env_vars = {
            "PROMPT_TEST_SOURCE": "local",
            "PROMPT_TEST_PATH": "/tmp/test.txt",
            "PROMPT_TEST_CACHE_TTL": "1800",
        }

        with patch.dict(os.environ, env_vars):
            config = PromptConfig.from_env("test")

            assert config is not None
            assert config.name == "test"
            assert config.source == SourceType.LOCAL
            assert config.source_config["path"] == "/tmp/test.txt"
            assert config.cache_ttl == 1800

    def test_prompt_config_from_env_not_found(self):
        """Test prompt config returns None when not in environment."""
        with patch.dict(os.environ, {}, clear=True):
            config = PromptConfig.from_env("nonexistent")
            assert config is None


class TestPromptManagerConfig:
    """Test PromptManagerConfig functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PromptManagerConfig()

        assert config.cache_enabled is True
        assert config.cache_ttl == 3600
        assert config.validate_on_startup == ValidationMode.ENV_ONLY
        assert config.openai_timeout == 30
        assert config.openai_max_retries == 3

    def test_config_from_env(self):
        """Test loading configuration from environment."""
        env_vars = {
            "PROMPT_MANAGER_CACHE_ENABLED": "false",
            "PROMPT_MANAGER_CACHE_TTL": "7200",
            "PROMPT_MANAGER_VALIDATE_ON_STARTUP": "load_test",
            "PROMPT_MANAGER_OPENAI_API_KEY": "sk-test",
            "PROMPT_MANAGER_PROMPTS_DIR": "/tmp/prompts",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = PromptManagerConfig.from_env()

            assert config.cache_enabled is False
            assert config.cache_ttl == 7200
            assert config.validate_on_startup == ValidationMode.LOAD_TEST
            assert config.openai_api_key == "sk-test"
            assert config.prompts_dir == "/tmp/prompts"

    def test_discover_prompts_from_env(self):
        """Test auto-discovery of prompts from environment."""
        env_vars = {
            "PROMPT_WELCOME_SOURCE": "openai",
            "PROMPT_WELCOME_ID": "pmpt_123",
            "PROMPT_GREETING_SOURCE": "local",
            "PROMPT_GREETING_PATH": "greeting.txt",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = PromptManagerConfig.from_env()

            assert len(config.prompts) == 2
            assert "welcome" in config.prompts
            assert "greeting" in config.prompts

            welcome = config.prompts["welcome"]
            assert welcome.source == SourceType.OPENAI
            assert welcome.source_config["prompt_id"] == "pmpt_123"

            greeting = config.prompts["greeting"]
            assert greeting.source == SourceType.LOCAL
            assert greeting.source_config["path"] == "greeting.txt"

    def test_validate_sources_no_sources(self):
        """Test validation fails when no sources configured."""
        config = PromptManagerConfig()
        errors = config.validate_sources()

        assert len(errors) > 0
        assert "No prompt sources configured" in errors[0]

    def test_validate_sources_missing_config(self):
        """Test validation catches missing prompt configuration."""
        config = PromptManagerConfig(
            openai_api_key="sk-test",
            prompts={
                "test": PromptConfig(
                    name="test",
                    source=SourceType.OPENAI,
                    source_config={},  # Missing prompt_id
                )
            },
        )

        errors = config.validate_sources()
        assert len(errors) > 0
        assert "prompt ID configured" in errors[0]


class TestSourceType:
    """Test SourceType enum functionality."""

    def test_source_type_values(self):
        """Test source type enum values."""
        assert SourceType.OPENAI.value == "openai"
        assert SourceType.LOCAL.value == "local"

    def test_source_type_from_string(self):
        """Test converting string to source type."""
        assert SourceType.from_string("openai") == SourceType.OPENAI
        assert SourceType.from_string("LOCAL") == SourceType.LOCAL
        assert SourceType.from_string("Local") == SourceType.LOCAL

    def test_source_type_from_string_invalid(self):
        """Test invalid source type raises error."""
        with pytest.raises(ConfigurationError) as exc_info:
            SourceType.from_string("invalid")

        assert "Invalid source type" in str(exc_info.value)


class TestValidationMode:
    """Test ValidationMode enum functionality."""

    def test_validation_mode_values(self):
        """Test validation mode enum values."""
        assert ValidationMode.NONE.value == "none"
        assert ValidationMode.ENV_ONLY.value == "env_only"
        assert ValidationMode.LOAD_TEST.value == "load_test"

    def test_validation_mode_from_string(self):
        """Test converting string to validation mode."""
        assert ValidationMode.from_string("none") == ValidationMode.NONE
        assert ValidationMode.from_string("ENV_ONLY") == ValidationMode.ENV_ONLY
        assert ValidationMode.from_string("Load_Test") == ValidationMode.LOAD_TEST

    def test_validation_mode_from_string_invalid(self):
        """Test invalid validation mode raises error."""
        with pytest.raises(ConfigurationError) as exc_info:
            ValidationMode.from_string("invalid")

        assert "Invalid validation mode" in str(exc_info.value)


class TestGlobalConfig:
    """Test global configuration management."""

    def test_get_config(self):
        """Test getting global config instance."""
        reset_config()  # Ensure clean state

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2  # Same instance

    def test_reset_config(self):
        """Test resetting global config."""
        config1 = get_config()
        reset_config()
        config2 = get_config()

        assert config1 is not config2  # Different instances
