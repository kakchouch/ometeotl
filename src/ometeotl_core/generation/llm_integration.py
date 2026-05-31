"""LLM-assisted context refinement for hybrid generation workflows.

This module is intentionally provider-agnostic. It accepts a callable text
producer and converts LLM text responses into deterministic GenerationContext
updates that can be validated by the regular generation pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .context import GenerationContext

TextGenerator = Callable[[str], str]
ResponseParser = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class LLMRefinementResult:
    """Result of one LLM refinement attempt."""

    refined_context: GenerationContext
    raw_response: str
    used_fallback: bool = False
    diagnostics: list[str] = field(default_factory=list)


class LLMGenerationAdapter:
    """Provider-neutral adapter for context -> prompt -> context refinement."""

    def __init__(
        self,
        *,
        text_generator: TextGenerator,
        response_parser: ResponseParser | None = None,
    ) -> None:
        self._text_generator = text_generator
        self._response_parser = response_parser or self._parse_json_mapping

    def render_prompt(
        self,
        context: GenerationContext,
        *,
        prompt_template: str | None = None,
    ) -> str:
        """Render a deterministic prompt from a generation context."""
        context_payload = {
            "kind": context.kind,
            "id": context.id,
            "attributes": dict(context.attributes),
            "relations": context.normalized_relations(),
            "state": dict(context.state),
            "context": dict(context.context),
            "metadata": dict(context.metadata),
        }
        serialized_context = json.dumps(context_payload, sort_keys=True)

        if prompt_template:
            return prompt_template.format(context_json=serialized_context)

        return (
            "Refine this ometeotl generation context and return a JSON object "
            "containing only context overrides. "
            f"Context: {serialized_context}"
        )

    def refine_context(
        self,
        context: GenerationContext,
        *,
        prompt_template: str | None = None,
        fallback_to_base: bool = True,
    ) -> LLMRefinementResult:
        """Produce a refined GenerationContext from an LLM response.

        When parsing fails and fallback_to_base=True, the original context is
        returned with diagnostics and used_fallback=True.
        """
        prompt = self.render_prompt(context, prompt_template=prompt_template)
        raw_response = self._text_generator(prompt)

        return self.refine_context_from_response(
            context,
            raw_response,
            fallback_to_base=fallback_to_base,
        )

    def refine_context_from_response(
        self,
        context: GenerationContext,
        raw_response: str,
        *,
        fallback_to_base: bool = True,
    ) -> LLMRefinementResult:
        """Refine a context from an already-produced LLM text response."""

        try:
            parsed = self._response_parser(raw_response)
            overrides = self._extract_overrides(parsed)
            refined = context.copy_with(**overrides)
            return LLMRefinementResult(
                refined_context=refined,
                raw_response=raw_response,
                used_fallback=False,
                diagnostics=[],
            )
        except Exception as exc:  # noqa: BLE001 - surface robust fallback path
            if not fallback_to_base:
                raise
            return LLMRefinementResult(
                refined_context=context,
                raw_response=raw_response,
                used_fallback=True,
                diagnostics=[
                    (
                        "LLM refinement parsing failed; falling back to base "
                        f"context: {exc}"
                    )
                ],
            )

    def _extract_overrides(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        allowed_keys = {
            "label",
            "attributes",
            "relations",
            "state",
            "context",
            "provenance",
            "metadata",
            "operation",
            "target_id",
            "registration_policy",
            "validate",
            "validation_mode",
            "stage_modes",
        }

        overrides: dict[str, Any] = {}
        for key in allowed_keys:
            if key not in payload:
                continue
            value = payload[key]
            if key in {
                "attributes",
                "state",
                "context",
                "provenance",
                "metadata",
                "stage_modes",
            }:
                overrides[key] = dict(value or {})
            elif key == "relations":
                overrides[key] = {
                    str(rel_name): [str(item) for item in rel_values or []]
                    for rel_name, rel_values in dict(value or {}).items()
                }
            elif key == "validate":
                overrides[key] = bool(value)
            else:
                overrides[key] = value

        return overrides

    def _parse_json_mapping(self, raw_response: str) -> Mapping[str, Any]:
        parsed = json.loads(raw_response)
        if not isinstance(parsed, Mapping):
            raise ValueError("LLM response must decode to a JSON object")
        return parsed
