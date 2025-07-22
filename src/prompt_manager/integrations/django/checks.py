"""Django system checks for prompt manager configuration."""

import os

from django.core.checks import Error, Tags, Warning, register


@register(Tags.compatibility)
def check_prompt_manager_configuration(app_configs, **kwargs):
    """Check prompt manager configuration for common issues."""
    errors = []

    # Check if any source is configured
    has_openai = bool(os.getenv("PROMPT_MANAGER_OPENAI_API_KEY"))
    has_local = bool(os.getenv("PROMPT_MANAGER_PROMPTS_DIR"))

    if not (has_openai or has_local):
        errors.append(
            Warning(
                "No prompt sources configured",
                hint=(
                    "Set either PROMPT_MANAGER_OPENAI_API_KEY or "
                    "PROMPT_MANAGER_PROMPTS_DIR environment variables to enable prompt management."
                ),
                id="prompt_manager.W001",
            )
        )

    # Check validation mode
    validation_mode = os.getenv(
        "PROMPT_MANAGER_VALIDATE_ON_STARTUP", "env_only"
    ).lower()
    valid_modes = ["none", "env_only", "load_test"]

    if validation_mode not in valid_modes:
        errors.append(
            Error(
                f"Invalid validation mode: {validation_mode}",
                hint=f"Valid modes are: {', '.join(valid_modes)}",
                id="prompt_manager.E001",
            )
        )

    # Check for prompt registrations
    prompt_count = 0
    for key in os.environ:
        if key.startswith("PROMPT_") and key.endswith("_SOURCE"):
            prompt_count += 1

    if prompt_count == 0 and (has_openai or has_local):
        errors.append(
            Warning(
                "No prompts registered via environment variables",
                hint=(
                    "Register prompts using PROMPT_{NAME}_SOURCE environment variables "
                    "or register them programmatically."
                ),
                id="prompt_manager.W002",
            )
        )

    return errors


@register(Tags.compatibility)
def check_prompt_manager_dependencies(app_configs, **kwargs):
    """Check if required dependencies are installed."""
    errors = []

    # Check for OpenAI if configured
    if os.getenv("PROMPT_MANAGER_OPENAI_API_KEY"):
        try:
            import openai  # noqa
        except ImportError:
            errors.append(
                Error(
                    "OpenAI library not installed",
                    hint="Install with: pip install python-prompt-manager[openai]",
                    id="prompt_manager.E002",
                )
            )

    # Check for YAML support if needed
    has_yaml_files = False
    prompts_dir = os.getenv("PROMPT_MANAGER_PROMPTS_DIR")
    if prompts_dir and os.path.exists(prompts_dir):
        for root, dirs, files in os.walk(prompts_dir):
            if any(f.endswith((".yaml", ".yml")) for f in files):
                has_yaml_files = True
                break

    if has_yaml_files:
        try:
            import yaml  # noqa
        except ImportError:
            errors.append(
                Warning(
                    "PyYAML not installed but YAML prompt files detected",
                    hint="Install with: pip install python-prompt-manager[yaml]",
                    id="prompt_manager.W003",
                )
            )

    return errors
