"""Test PromptManager with dictionary configuration."""

from unittest.mock import Mock, patch

import pytest

from prompt_manager import PromptManager
from prompt_manager.core.exceptions import PromptNotRegisteredError


class TestPromptManagerDictConfig:
    """Test PromptManager with dictionary configuration."""

    def test_init_with_dict_config(self):
        """Test initializing PromptManager with a dictionary."""
        config = {
            "prompts": {"test_prompt": {"source": "local", "path": "test.txt"}},
            "sources": {"local": {"base_dir": "/tmp/prompts"}},
        }

        manager = PromptManager(config)
        assert len(manager.config.prompts) == 1
        assert "test_prompt" in manager.config.prompts
        assert manager.config.prompts_dir == "/tmp/prompts"

    def test_dict_config_with_openai(self):
        """Test dictionary config with OpenAI settings."""
        config = {
            "prompts": {
                "ai_prompt": {
                    "source": "openai",
                    "id": "pmpt_123",
                    "version": "1.0",
                    "cache_ttl": 300,
                }
            },
            "sources": {
                "openai": {"api_key": "test-key", "timeout": 60, "max_retries": 2}
            },
            "cache_ttl": 3600,
            "validate_on_startup": False,
        }

        manager = PromptManager(config)

        # Check OpenAI config
        assert manager.config.openai_api_key == "test-key"
        assert manager.config.openai_timeout == 60
        assert manager.config.openai_max_retries == 2

        # Check prompt config
        prompt_config = manager.config.prompts["ai_prompt"]
        assert prompt_config.source_config["prompt_id"] == "pmpt_123"
        assert prompt_config.source_config["version"] == "1.0"
        assert prompt_config.cache_ttl == 300

        # Check global config
        assert manager.config.cache_ttl == 3600

    def test_dict_config_boolean_validate(self):
        """Test boolean validate_on_startup conversion."""
        # Test with True (need sources configured for validation)
        config_true = {
            "prompts": {},
            "sources": {"local": {"base_dir": "/tmp"}},
            "validate_on_startup": True,
        }
        manager = PromptManager(config_true)
        assert manager.config.validate_on_startup.value == "load_test"

        # Test with False
        config_false = {"prompts": {}, "validate_on_startup": False}
        manager = PromptManager(config_false)
        assert manager.config.validate_on_startup.value == "none"

    def test_get_method_alias(self, temp_prompts_dir):
        """Test that get() method works as alias for get_prompt()."""
        config = {
            "prompts": {"greeting": {"source": "local", "path": "greeting.txt"}},
            "sources": {"local": {"base_dir": temp_prompts_dir}},
        }

        manager = PromptManager(config)

        # Both methods should return the same result
        result1 = manager.get("greeting")
        result2 = manager.get_prompt("greeting")
        assert result1 == result2 == "Hello {name}!"

        # Test with variables
        result_with_vars = manager.get("greeting", variables={"name": "World"})
        assert result_with_vars == "Hello World!"

    def test_dict_config_matches_readme_example(self, mock_openai_client):
        """Test that README example configuration works."""
        # This is the exact format shown in the README
        config = {
            "prompts": {
                "welcome": {
                    "source": "openai",
                    "id": "pmpt_1234567890",
                    "version": "1.0",
                },
                "greeting": {"source": "local", "path": "greeting.txt"},
            },
            "sources": {
                "openai": {"api_key": "test-key", "timeout": 30, "max_retries": 3},
                "local": {"base_dir": "./prompts"},
            },
        }

        manager = PromptManager(config)

        # Verify configuration was parsed correctly
        assert len(manager.config.prompts) == 2
        assert manager.config.openai_api_key == "test-key"
        assert manager.config.prompts_dir == "./prompts"

        # Verify prompt configs
        welcome_config = manager.config.prompts["welcome"]
        assert welcome_config.source_config["prompt_id"] == "pmpt_1234567890"
        assert welcome_config.source_config["version"] == "1.0"

        greeting_config = manager.config.prompts["greeting"]
        assert greeting_config.source_config["path"] == "greeting.txt"
