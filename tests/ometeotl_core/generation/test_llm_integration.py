"""Tests for generation LLM integration adapter and hybrid pipeline mode."""

from __future__ import annotations

from ometeotl_core.generation import (
    ContextualGenerationPipeline,
    GenerationContext,
    LLMGenerationAdapter,
)
from ometeotl_core.validation import (
    SEVERITY_ERROR,
    ValidationContext,
    ValidationIssue,
    ValidationPipeline,
    ValidationResult,
)


class _FailWithSuggestionValidator:
    @property
    def name(self) -> str:
        return "fail_with_suggestion"

    def validate(self, obj, context: ValidationContext) -> ValidationResult:
        return ValidationResult(
            stage=context.stage,
            policy_mode=context.policy_mode,
            issues=[
                ValidationIssue(
                    code="GEN-SUGGEST",
                    severity=SEVERITY_ERROR,
                    message="Synthetic failure with fix guidance",
                    object_id=str(getattr(obj, "id", "")),
                    suggestion="Set required actor_id in metadata",
                )
            ],
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


def test_llm_adapter_parses_markdown_wrapped_json_response():
    def fake_generator(prompt: str) -> str:
        del prompt
        return """```json
{
    \"label\": \"Wrapped\",
    \"attributes\": {\"kind\": \"custom\"}
}
```"""

    adapter = LLMGenerationAdapter(text_generator=fake_generator)
    base_context = GenerationContext(kind="actor", id="actor-hybrid-2c", label="Base")

    refinement = adapter.refine_context(base_context)

    assert refinement.used_fallback is False
    assert refinement.refined_context.label == "Wrapped"
    assert refinement.refined_context.attributes["kind"] == "custom"


def test_llm_adapter_falls_back_when_text_generator_raises():
    def failing_generator(prompt: str) -> str:
        del prompt
        raise RuntimeError("provider timeout")

    adapter = LLMGenerationAdapter(text_generator=failing_generator)
    base_context = GenerationContext(kind="actor", id="actor-hybrid-2b", label="Base")

    refinement = adapter.refine_context(base_context, fallback_to_base=True)

    assert refinement.used_fallback is True
    assert refinement.refined_context.id == "actor-hybrid-2b"
    assert refinement.raw_response == ""
    assert any("generation failed" in msg.lower() for msg in refinement.diagnostics)


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
    assert "stage: text_generation" in result.diagnostics
    assert "stage: parsing" in result.diagnostics
    assert "stage: instantiation (create)" in result.diagnostics


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


def test_pipeline_generate_from_text_response_parses_and_instantiates():
    adapter = LLMGenerationAdapter(text_generator=lambda prompt: "{}")
    pipeline = ContextualGenerationPipeline()

    result = pipeline.generate_from_text_response(
        GenerationContext(kind="actor", id="actor-hybrid-5", label="Base"),
        raw_response='{"label": "FromText", "attributes": {"kind": "custom"}}',
        llm_adapter=adapter,
    )

    assert result.generated.id == "actor-hybrid-5"
    assert result.generated.label == "FromText"
    assert "stage: parsing" in result.diagnostics
    assert "stage: instantiation (create)" in result.diagnostics


def test_pipeline_reports_uncertainty_zones_from_context_metadata():
    adapter = LLMGenerationAdapter(text_generator=lambda prompt: "{}")
    pipeline = ContextualGenerationPipeline()

    result = pipeline.generate_hybrid(
        GenerationContext(
            kind="actor",
            id="actor-hybrid-6",
            metadata={"uncertainty_zones": ["zone-a", "zone-b"]},
        ),
        llm_adapter=adapter,
    )

    assert result.uncertainty_zones == ["zone-a", "zone-b"]
    assert any("uncertainty zones" in msg.lower() for msg in result.diagnostics)


def test_pipeline_builds_repair_suggestions_on_validation_failure():
    adapter = LLMGenerationAdapter(text_generator=lambda prompt: "{}")
    pipeline = ContextualGenerationPipeline(
        validation_pipeline=ValidationPipeline(
            validators=[_FailWithSuggestionValidator()]
        )
    )

    result = pipeline.generate_hybrid(
        GenerationContext(
            kind="actor",
            id="actor-hybrid-7",
            validate=True,
        ),
        llm_adapter=adapter,
    )

    assert result.validation is not None
    assert result.validation.valid is False
    assert result.repair_suggestions == ["Set required actor_id in metadata"]
    assert any("Suggested repair" in msg for msg in result.diagnostics)
