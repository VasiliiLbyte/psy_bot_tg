"""Tests for stage → OpenRouter model mapping."""

from __future__ import annotations

import model_router


def test_known_stages_map_to_configured_model() -> None:
    for stage in (
        "symptom_collection",
        "context_collection",
        "evaluation",
        "recommendations",
    ):
        m = model_router.get_model_for_stage(stage)
        assert m == "deepseek/deepseek-r1"


def test_unknown_stage_falls_back_to_default() -> None:
    assert model_router.get_model_for_stage("unknown_stage_xyz") == model_router.DEFAULT_MODEL
