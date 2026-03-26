"""Model selection per pipeline stage (stage 3).

Maps each FSM stage to an appropriate OpenRouter model.
The primary diagnostic model is deepseek/deepseek-r1 as specified
in context-management.md.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_STAGE_MODEL_MAP: dict[str, str] = {
    "evaluation": "deepseek/deepseek-r1",
    "symptom_collection": "openai/gpt-4o-mini",
    "context_collection": "openai/gpt-4o-mini",
    "recommendations": "openai/gpt-4o",
}

DEFAULT_MODEL = "deepseek/deepseek-r1"

_ENV_OVERRIDE_BY_STAGE: dict[str, str] = {
    "symptom_collection": "MODEL_SYMPTOM_COLLECTION",
    "context_collection": "MODEL_SYMPTOM_COLLECTION",
    "evaluation": "MODEL_EVALUATION",
    "recommendations": "MODEL_RECOMMENDATIONS",
}


def get_model_for_stage(stage: str) -> str:
    """Return the OpenRouter model identifier for a given pipeline stage."""
    env_key = _ENV_OVERRIDE_BY_STAGE.get(stage)
    if env_key:
        override = os.getenv(env_key, "").strip()
        if override:
            logger.debug("Stage '%s' → model '%s' (override %s)", stage, override, env_key)
            return override
    model = _STAGE_MODEL_MAP.get(stage, DEFAULT_MODEL)
    logger.debug("Stage '%s' → model '%s'", stage, model)
    return model
