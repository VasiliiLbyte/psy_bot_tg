"""Tests for stage → OpenRouter model mapping."""

from __future__ import annotations

import os

import model_router


def test_known_stages_map_to_configured_model() -> None:
    assert model_router.get_model_for_stage("symptom_collection") == "openai/gpt-4o-mini"
    assert model_router.get_model_for_stage("context_collection") == "openai/gpt-4o-mini"
    assert model_router.get_model_for_stage("evaluation") == "deepseek/deepseek-r1"
    assert model_router.get_model_for_stage("recommendations") == "anthropic/claude-3.5-sonnet"


def test_unknown_stage_falls_back_to_default() -> None:
    assert model_router.get_model_for_stage("unknown_stage_xyz") == model_router.DEFAULT_MODEL


def test_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_SYMPTOM_COLLECTION", "x/symptom")
    monkeypatch.setenv("MODEL_EVALUATION", "x/eval")
    monkeypatch.setenv("MODEL_RECOMMENDATIONS", "x/reco")

    assert model_router.get_model_for_stage("symptom_collection") == "x/symptom"
    assert model_router.get_model_for_stage("context_collection") == "x/symptom"
    assert model_router.get_model_for_stage("evaluation") == "x/eval"
    assert model_router.get_model_for_stage("recommendations") == "x/reco"
