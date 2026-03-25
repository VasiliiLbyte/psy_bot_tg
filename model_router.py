"""Model selection per pipeline stage (stage 3).

Maps each FSM stage to an appropriate OpenRouter model.
The primary diagnostic model is deepseek/deepseek-r1 as specified
in context-management.md.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_STAGE_MODEL_MAP: dict[str, str] = {
    "symptom_collection": "deepseek/deepseek-r1",
    "context_collection": "deepseek/deepseek-r1",
    "evaluation": "deepseek/deepseek-r1",
    "recommendations": "deepseek/deepseek-r1",
}

DEFAULT_MODEL = "deepseek/deepseek-r1"


def get_model_for_stage(stage: str) -> str:
    """Return the OpenRouter model identifier for a given pipeline stage."""
    model = _STAGE_MODEL_MAP.get(stage, DEFAULT_MODEL)
    logger.debug("Stage '%s' → model '%s'", stage, model)
    return model
