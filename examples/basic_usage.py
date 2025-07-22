"""Basic usage examples for python-prompt-manager."""

import os
from prompt_manager import PromptManager, get_prompt

# Example 1: Using environment variables
# Set these before running:
# export PROMPT_MANAGER_OPENAI_API_KEY="sk-..."
# export PROMPT_WELCOME_SOURCE="openai"
# export PROMPT_WELCOME_ID="pmpt_123..."

def example_env_config():
    """Example using environment variable configuration."""
    print("=== Example 1: Environment Configuration ===")
    
    # Get prompt using global instance
    try:
        prompt = get_prompt("welcome")
        print(f"Welcome prompt: {prompt}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to set the required environment variables")


# Example 2: Programmatic configuration
def example_programmatic():
    """Example using programmatic configuration."""
    print("\n=== Example 2: Programmatic Configuration ===")
    
    # Create manager instance
    pm = PromptManager()
    
    # Register a prompt
    pm.register_prompt(
        name="greeting",
        source="local",
        source_config={
            "path": "examples/prompts/greeting.txt"
        }
    )
    
    # Use the prompt
    prompt = pm.get_prompt("greeting", variables={
        "name": "Alice",
        "time": "morning"
    })
    print(f"Greeting: {prompt}")


# Example 3: Using defaults and error handling
def example_with_defaults():
    """Example with default values and error handling."""
    print("\n=== Example 3: Defaults and Error Handling ===")
    
    pm = PromptManager()
    
    # Try to get a prompt that might not exist
    prompt = pm.get_prompt(
        "optional_feature",
        default="Welcome to our application!",
        variables={"user": "Guest"}
    )
    print(f"Prompt with default: {prompt}")


# Example 4: Multiple sources
def example_multiple_sources():
    """Example using multiple prompt sources."""
    print("\n=== Example 4: Multiple Sources ===")
    
    pm = PromptManager()
    
    # Register prompts from different sources
    # OpenAI prompt
    pm.register_prompt(
        name="analysis",
        source="openai",
        source_config={
            "prompt_id": "pmpt_analysis_v1"
        },
        cache_ttl=3600  # Cache for 1 hour
    )
    
    # Local file prompt
    pm.register_prompt(
        name="summary",
        source="local",
        source_config={
            "path": "templates/summary.txt"
        },
        cache_ttl=300  # Cache for 5 minutes
    )
    
    print("Registered prompts:", pm.list_prompts())


# Example 5: Cache management
def example_cache_management():
    """Example of cache management."""
    print("\n=== Example 5: Cache Management ===")
    
    pm = PromptManager()
    
    # Register a prompt with no caching
    pm.register_prompt(
        name="dynamic",
        source="local",
        source_config={"path": "dynamic.txt"},
        cache_ttl=0  # No caching
    )
    
    # Clear all cache
    pm.clear_cache()
    print("Cache cleared")


if __name__ == "__main__":
    # Run examples
    example_env_config()
    example_programmatic()
    example_with_defaults()
    example_multiple_sources()
    example_cache_management()