"""LLM provider abstraction.

The LLM only *explains* recommendations produced by the rules engine. It never
chooses materials or processes and must not invent dimensions. Output is JSON
validated against `Explanation`.

Providers:
  anthropic  Anthropic API (needs ANTHROPIC_API_KEY)
  mock       deterministic, offline; used in tests and demos
  none       LLM disabled; the app works without it
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from app.config import settings


class Explanation(BaseModel):
    plain_summary: str = Field(description="2-4 sentences in plain language for a non-engineer.")
    tradeoffs: list[str] = Field(description="Key trade-offs between the recommendation and its alternatives.")
    questions_to_consider: list[str] = Field(description="Questions the product owner should answer next.")
    caveats: list[str] = Field(description="What is uncertain or must be verified (e.g. unverified data, safety).")


class LLMUnavailable(RuntimeError):
    pass


class LLMProvider(Protocol):
    name: str

    def explain(self, recommendation: dict[str, Any]) -> Explanation: ...


SYSTEM_PROMPT = """You explain manufacturing recommendations to a product designer who is not a mechanical engineer.

You receive a recommendation produced by a deterministic rules engine, as JSON. Your job is to explain it, not to change it:
- Do not recommend a different material or process than the one given; you may discuss the listed alternatives.
- Do not invent dimensions, tolerances, prices or specifications. Only use numbers present in the input, and label anything inferred as an assumption.
- Treat rule data marked verified=false as unverified general guidance, and say so where it matters.
- Repeat every safety flag as a caveat that needs human or manufacturer verification.
- Use plain language first; keep technical terms brief and explained."""


def _compact(rec: dict[str, Any]) -> dict[str, Any]:
    keys = ["part_name", "recommendation", "summary", "reason", "assumptions", "confidence", "confidence_reason",
            "alternatives", "volume_sensitivity", "open_questions", "risks", "technical", "safety_flags", "sources"]
    return {k: rec.get(k) for k in keys}


class MockProvider:
    """Deterministic explanation assembled from the recommendation itself."""

    name = "mock"

    def explain(self, recommendation: dict[str, Any]) -> Explanation:
        rec = recommendation.get("recommendation") or {}
        alts = recommendation.get("alternatives") or []
        caveats = [f"Safety: {f['message']}" for f in recommendation.get("safety_flags", [])]
        if recommendation.get("uses_unverified_data"):
            caveats.append("Based on unverified, model-generated rule data. Confirm with suppliers.")
        return Explanation(
            plain_summary=(
                f"[mock] For the {recommendation.get('part_name', 'part')}, the rules suggest "
                f"{rec.get('process_name', 'no process')} in {rec.get('material_name', 'no material')}. "
                f"Confidence is {recommendation.get('confidence')}: {recommendation.get('confidence_reason', '')}"
            ),
            tradeoffs=[f"{a['process_name']}: {a['when_to_prefer']}" for a in alts],
            questions_to_consider=list(recommendation.get("open_questions", [])),
            caveats=caveats,
        )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str) -> None:
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model

    def explain(self, recommendation: dict[str, Any]) -> Explanation:
        schema = Explanation.model_json_schema()
        schema["additionalProperties"] = False
        try:
            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
                messages=[{
                    "role": "user",
                    "content": "Explain this recommendation.\n\n" + json.dumps(_compact(recommendation), indent=1),
                }],
            )
        except self._anthropic.APIStatusError as e:
            raise LLMUnavailable(f"Anthropic API error {e.status_code}: {e.message}") from e
        except self._anthropic.APIConnectionError as e:
            raise LLMUnavailable(f"Could not reach the Anthropic API: {e}") from e

        if response.stop_reason == "refusal":
            raise LLMUnavailable("The model declined to explain this recommendation.")
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            return Explanation.model_validate_json(text)
        except ValidationError as e:
            raise LLMUnavailable(f"LLM returned invalid JSON: {e}") from e


_provider: LLMProvider | None = None


def get_provider() -> LLMProvider | None:
    """The configured provider, or None when the LLM is disabled."""
    global _provider
    if settings.llm_provider == "none":
        return None
    if _provider is None:
        if settings.llm_provider == "mock":
            _provider = MockProvider()
        elif settings.llm_provider == "anthropic":
            _provider = AnthropicProvider(settings.anthropic_model)
        else:
            raise LLMUnavailable(f"Unknown LLM provider {settings.llm_provider!r}")
    return _provider
