"""Pytest configuration and shared fixtures."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_prompts_dir():
    """Create a temporary directory with test prompt files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        prompts_dir.mkdir()
        
        # Create test prompt files
        (prompts_dir / "greeting.txt").write_text("Hello {name}!")
        (prompts_dir / "welcome.txt").write_text("Welcome to our service")
        
        yield str(prompts_dir)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch("prompt_manager.sources.openai.OpenAI") as mock_class:
        mock_client = Mock()
        mock_class.return_value = mock_client
        
        # Mock response structure
        mock_response = Mock()
        mock_response.instructions = [Mock()]
        mock_response.instructions[0].content = [Mock()]
        mock_response.instructions[0].content[0].text = "Test prompt content"
        
        mock_client.responses.create.return_value = mock_response
        
        yield mock_client


@pytest.fixture
def sample_config(temp_prompts_dir):
    """Sample configuration for testing."""
    return {
        "prompts": {
            "welcome": {"source": "local", "path": "welcome.txt"},
            "greeting": {"source": "local", "path": "greeting.txt"},
            "openai_test": {"source": "openai", "id": "pmpt_test123"},
        },
        "sources": {
            "local": {"base_dir": temp_prompts_dir},
            "openai": {"api_key": "test-key"},
        },
        "cache_ttl": 300,
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset any global state
    from prompt_manager.core.config import reset_config
    from prompt_manager.core.manager import reset_prompt_manager
    
    reset_config()
    reset_prompt_manager()
    
    yield
    
    # Cleanup after test
    reset_config()
    reset_prompt_manager()


@pytest.fixture
def env_setup(monkeypatch):
    """Set up environment variables for testing."""
    def _setup(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, str(value))
    return _setup