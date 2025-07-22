"""Simple, pragmatic configuration example for prompt-manager."""

import os
from prompt_manager import PromptManager

# This is how developers actually want to configure prompts
PROMPT_CONFIG = {
    "prompts": {
        # OpenAI prompts with versions
        "welcome_message": {
            "source": "openai",
            "id": "pmpt_welcome_v2",
            "version": "2.0"
        },
        "user_analysis": {
            "source": "openai", 
            "id": "pmpt_analysis_v1",
            "version": "1.0",
            "cache_ttl": 300  # 5 minutes for dynamic prompts
        },
        
        # Local file prompts
        "email_template": {
            "source": "local",
            "path": "templates/welcome_email.txt"
        },
        "error_message": {
            "source": "local",
            "path": "templates/error.txt",
            "cache_ttl": 0  # Don't cache, might change frequently
        }
    },
    
    # Source configuration
    "sources": {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY"),  # Always use env for secrets
            "timeout": 30
        },
        "local": {
            "base_dir": "./prompts"
        }
    },
    
    # Global defaults
    "cache_ttl": 3600,  # 1 hour default
    "validate_on_startup": True  # Fail fast in production
}

# Usage is simple and obvious
pm = PromptManager(PROMPT_CONFIG)

# Get prompts
welcome = pm.get("welcome_message")
email = pm.get("email_template", variables={"name": "John", "company": "Acme"})

# With fallback
message = pm.get("optional_prompt", default="Hello there!")

# For Django projects, just put this in settings.py:
# PROMPT_MANAGER = PROMPT_CONFIG