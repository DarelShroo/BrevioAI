from __future__ import annotations

from typing import Any, Protocol

from .models import JUDGE_VERSION


class SemanticJudge(Protocol):
    enabled: bool
    model: str
    version: str

    def evaluate(self, record: dict[str, Any]) -> dict[str, Any]:
        ...


class DisabledJudge:
    enabled = False
    model = "disabled"
    version = JUDGE_VERSION

    def evaluate(self, record: dict[str, Any]) -> dict[str, Any]:
        del record
        return {
            "enabled": False,
            "status": "disabled",
            "model": self.model,
            "version": self.version,
            "cost": None,
            "tokens": None,
        }


class ConfiguredJudge:
    """Optional LLM judge. Not a substitute for gold/claim scoring.

    The generation pass never calls this automatically. Invoke it from a
    dedicated command so generator and judge remain separable, and so tests
    never hit a live model.
    """

    enabled = True
    version = JUDGE_VERSION

    def __init__(self, model: str, *, provider: str = "ollama") -> None:
        if not (model or "").strip():
            raise ValueError("ConfiguredJudge requires a model name")
        self.model = model.strip()
        self.provider = provider

    def evaluate(self, record: dict[str, Any]) -> dict[str, Any]:
        from pathlib import Path

        from .semantic_evaluator import evaluate_record

        return evaluate_record(
            record,
            repository_root=Path(__file__).resolve().parents[2],
            model=self.model,
        )


def create_judge(model: str) -> DisabledJudge | ConfiguredJudge:
    name = (model or "").strip()
    if not name:
        return DisabledJudge()
    return ConfiguredJudge(name)


def judge_metadata(model: str, generator_model: str) -> dict[str, Any]:
    judge = create_judge(model)
    return {
        "model": judge.model,
        "version": judge.version,
        "enabled": judge.enabled,
        "equals_generator": judge.enabled and judge.model == generator_model,
        "status": "configured" if judge.enabled else "disabled",
    }
