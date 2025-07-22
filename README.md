# Python Prompt Manager

A lightweight, extensible prompt management system for LLM applications. Centralize and version your prompts while keeping your codebase clean.

[![PyPI version](https://badge.fury.io/py/python-prompt-manager.svg)](https://badge.fury.io/py/python-prompt-manager)
[![Python Support](https://img.shields.io/pypi/pyversions/python-prompt-manager.svg)](https://pypi.org/project/python-prompt-manager/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why Use This?

Managing prompts for LLM applications can quickly become messy. Hardcoded strings, scattered prompt files / urls, and unclear versioning make maintenance difficult. This package solves these problems by providing a clean, centralized way to manage your prompts.

## Features

- **Multiple Storage Backends**: Store prompts in OpenAI's system, local files, or create your own storage extension
- **Environment-Based Configuration**: No hardcoded secrets or paths in your code
- **Flexible Caching**: Reduce API calls with configurable caching
- **Framework Agnostic**: Use with any Python framework or standalone scripts
- **Type Safe**: Full type hints for better development experience
- **Extensible**: Easy to add new storage backends

## Installation

```bash
# Basic installation
pip install python-prompt-manager

# With OpenAI support
pip install python-prompt-manager[openai]

# With all optional dependencies
pip install python-prompt-manager[all]
```

## Quick Start

### Basic Usage

```python
from prompt_manager import get_prompt

# Get a prompt (reads from configured source)
prompt = get_prompt("welcome_message")
print(prompt)
```

### With Variables

```python
# Use template variables in your prompts
prompt = get_prompt(
    "greeting", 
    variables={"name": "Alice", "day": "Monday"}
)
# "Hello Alice! Happy Monday!"
```

## Configuration

Configure your prompts using a simple Python dictionary:

```python
PROMPT_CONFIG = {
    "prompts": {
        "welcome": {
            "source": "openai",
            "id": "pmpt_1234567890",
            "version": "1.0"
        },
        "greeting": {
            "source": "local",
            "path": "greeting.txt"
        },
        "analysis": {
            "source": "openai",
            "id": "pmpt_0987654321",
            "cache_ttl": 300  # 5 minutes
        }
    },
    "sources": {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY"),  # Keep secrets in env vars
            "timeout": 30,
            "max_retries": 3
        },
        "local": {
            "base_dir": "./prompts"
        }
    }
}

# Initialize with your config
from prompt_manager import PromptManager
pm = PromptManager(PROMPT_CONFIG)
```

### Django Configuration

In your Django settings:

```python
# settings.py
PROMPT_MANAGER = {
    "prompts": {
        "welcome": {"source": "openai", "id": "pmpt_123"},
        "email_template": {"source": "local", "path": "emails/welcome.txt"}
    },
    "sources": {
        "openai": {
            "api_key": env("OPENAI_API_KEY")
        }
    }
}
```

## Usage Examples

### Simple Example

```python
from prompt_manager import PromptManager

# Initialize with config
pm = PromptManager({
    "prompts": {
        "welcome": {"source": "openai", "id": "pmpt_123"},
        "goodbye": {"source": "local", "path": "goodbye.txt"}
    }
})

# Get prompts
welcome = pm.get("welcome")
goodbye = pm.get("goodbye")
```

### With Default Fallback

```python
# Provide a default if prompt is not found
prompt = pm.get("optional_prompt", default="This is a fallback prompt")
```

### Dynamic Configuration

```python
# Load config from a file
import json

with open("prompts.json") as f:
    config = json.load(f)

pm = PromptManager(config)
```

### Template Variables

```python
# Configure a prompt with variables
config = {
    "prompts": {
        "greeting": {"source": "local", "path": "greeting.txt"}
    }
}

pm = PromptManager(config)

# Apply variables when retrieving
prompt = pm.get(
    "greeting",
    variables={"name": "Alice", "app_name": "AwesomeApp"}
)
# "Hello Alice! Welcome to AwesomeApp."
```

## Django Integration

Add your prompt configuration to settings:

```python
# settings.py
PROMPT_MANAGER = {
    "prompts": {
        "welcome_email": {"source": "openai", "id": "pmpt_email_123"},
        "user_greeting": {"source": "local", "path": "templates/greeting.txt"},
        "error_message": {"source": "openai", "id": "pmpt_error_456"}
    },
    "sources": {
        "openai": {"api_key": env("OPENAI_API_KEY")}
    }
}

# Optional: Add the Django app for additional features
INSTALLED_APPS = [
    ...
    'prompt_manager.integrations.django',  # Optional
]
```

Use in your views:

```python
# views.py
from django.conf import settings
from prompt_manager import PromptManager

# Initialize once
pm = PromptManager(settings.PROMPT_MANAGER)

def my_view(request):
    prompt = pm.get("welcome_email", variables={"user": request.user.name})
    # Use prompt with your LLM
    ...
```

## Validation

By default, prompts are validated when first accessed. To validate all prompts on startup:

```python
config = {
    "prompts": {...},
    "validate_on_startup": True  # Validate all prompts exist
}

pm = PromptManager(config)
```

## Advanced Usage

### Error Handling

```python
from prompt_manager import PromptManager, PromptNotFoundError

pm = PromptManager(config)

try:
    prompt = pm.get("my_prompt")
except PromptNotFoundError:
    # Handle missing prompt
    logger.error("Prompt not found")
except Exception as e:
    # Handle other errors
    logger.error(f"Error loading prompt: {e}")
```

### Caching

```python
# Configure cache TTL per prompt
config = {
    "prompts": {
        "static_prompt": {"source": "local", "path": "static.txt"},  # Uses default cache
        "dynamic_prompt": {"source": "openai", "id": "pmpt_123", "cache_ttl": 0}  # No cache
    },
    "cache_ttl": 3600  # Default 1 hour
}

# Clear cache manually
pm.clear_cache()
```

### Custom Sources

Extend the base class to add new sources:

```python
from prompt_manager.sources.base import BasePromptSource

class DatabaseSource(BasePromptSource):
    def fetch(self, config):
        # Your implementation
        return prompt_content
```

## Best Practices

1. **Keep Secrets in Environment Variables**: API keys should never be in code
2. **Use Clear Naming**: Choose descriptive names for your prompts
3. **Set Appropriate Cache TTLs**: Static prompts can cache longer than dynamic ones
4. **Handle Errors Gracefully**: Always provide fallbacks for critical prompts
5. **Version Your Prompts**: Use the version field to track prompt iterations

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/python-prompt-manager.git
cd python-prompt-manager

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
black src tests
flake8 src tests
mypy src
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for the modern LLM application stack
- Designed with production use in mind