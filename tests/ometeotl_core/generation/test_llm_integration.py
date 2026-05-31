"""Tests for generation LLM integration adapter and hybrid pipeline mode."""

from __future__ import annotations

from ometeotl_core.generation import (
    ContextualGenerationPipeline,
    GenerationContext,
    LLMGenerationAdapter,
)


def test_llm_adapter_refines_context_from_json_overrides():
    prompts: list[str] = []

    def fake_generator(prompt: str) -> str:
        prompts.append(prompt)
        return '{"attributes": {"kind": "custom"}, "label": "Refined"}'

    adapter = LLMGenerationAdapter(text_generator=fake_generator)
    base_context = GenerationContext(kind="actor", id="actor-hybrid-1", label="Base")

    refinement = adapter.refine_context(base_context)

    assert prompts
    assert refinement.used_fallback is False
    assert refinement.refined_context.label == "Refined"
    assert refinement.refined_context.attributes["kind"] == "custom"


def test_llm_adapter_falls_back_on_invalid_json_response():
    def fake_generator(prompt: str) -> str:
        del prompt
        return "not-json"

    adapter = LLMGenerationAdapter(text_generator=fake_generator)
    base_context = GenerationContext(kind="actor", id="actor-hybrid-2", label="Base")

    refinement = adapter.refine_context(base_context)

    assert refinement.used_fallback is True
    assert refinement.refined_context.id == "actor-hybrid-2"
    assert any("falling back" in msg.lower() for msg in refinement.diagnostics)


def test_pipeline_generate_hybrid_uses_llm_refined_context():
    def fake_generator(prompt: str) -> str:
        del prompt
        return '{"label": "Hybrid Actor", "attributes": {"kind": "custom"}}'

    adapter = LLMGenerationAdapter(text_generator=fake_generator)
    pipeline = ContextualGenerationPipeline()

    result = pipeline.generate_hybrid(
        GenerationContext(kind="actor", id="actor-hybrid-3", label="Base"),
        llm_adapter=adapter,
    )

    assert result.generated.id == "actor-hybrid-3"
    assert result.generated.label == "Hybrid Actor"
    assert result.generated.attributes["kind"] == "custom"


def test_pipeline_generate_hybrid_preserves_generation_when_fallback_needed():
    def fake_generator(prompt: str) -> str:
        del prompt
        return "invalid-json"

    adapter = LLMGenerationAdapter(text_generator=fake_generator)
    pipeline = ContextualGenerationPipeline()

    result = pipeline.generate_hybrid(
        GenerationContext(kind="actor", id="actor-hybrid-4", label="Base"),
        llm_adapter=adapter,
        fallback_to_base=True,
    )

    assert result.generated.id == "actor-hybrid-4"
    assert result.generated.label == "Base"
    assert any("falling back" in msg.lower() for msg in result.diagnostics)
