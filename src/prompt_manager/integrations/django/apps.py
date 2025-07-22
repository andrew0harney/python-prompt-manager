"""Django app configuration for python-prompt-manager."""

import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class PromptManagerConfig(AppConfig):
    """Django app configuration for prompt manager integration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "prompt_manager.integrations.django"
    label = "prompt_manager"
    verbose_name = "Prompt Manager"

    def ready(self):
        """Initialize prompt manager when Django starts."""
        # Import here to avoid circular imports
        from ...core.config import ValidationMode
        from ...core.manager import get_prompt_manager

        # Check if we should validate on startup
        validate_mode = getattr(
            settings,
            "PROMPT_MANAGER_VALIDATE_ON_STARTUP",
            ValidationMode.ENV_ONLY.value,
        )

        # Initialize the prompt manager
        try:
            manager = get_prompt_manager()
            logger.info(
                f"Prompt Manager initialized with {len(manager.list_prompts())} prompts"
            )

            # Validate if not in test mode
            if not getattr(settings, "TESTING", False):
                if validate_mode != ValidationMode.NONE.value:
                    manager.validate(ValidationMode.from_string(validate_mode))

        except Exception as e:
            logger.error(f"Failed to initialize Prompt Manager: {e}")
            # Re-raise in production to fail fast
            if not settings.DEBUG:
                raise
