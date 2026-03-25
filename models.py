"""Pydantic models for structured output (stage 4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiagnosticReport(BaseModel):
    """Structured preliminary assessment (not a medical diagnosis)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    preliminary_summary: str = Field(
        ...,
        min_length=1,
        description="Краткое резюме жалоб и контекста без постановки диагноза.",
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="На что обратить внимание или что уточнить на приёме.",
    )
    specialist_recommendations: list[str] = Field(
        default_factory=list,
        description="Рекомендуемые специалисты или профили помощи (очно).",
    )
    self_care_suggestions: list[str] = Field(
        default_factory=list,
        description="Безопасные общие рекомендации; не замена очной консультации.",
    )
    urgent_seek_care: bool = Field(
        default=False,
        description="True, если по симптомам уместно срочно обратиться к врачу или скорой.",
    )

    @staticmethod
    def _normalize_str_list(value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        out: list[str] = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out

    @field_validator("key_points", mode="before")
    @classmethod
    def v_key_points(cls, v: object) -> list[str]:
        return cls._normalize_str_list(v)

    @field_validator("specialist_recommendations", mode="before")
    @classmethod
    def v_specialists(cls, v: object) -> list[str]:
        return cls._normalize_str_list(v)

    @field_validator("self_care_suggestions", mode="before")
    @classmethod
    def v_self_care(cls, v: object) -> list[str]:
        return cls._normalize_str_list(v)
