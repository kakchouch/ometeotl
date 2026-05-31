"""Tests for the pluggable generation rule engine."""

import pytest

from ometeotl_core.generation import (
    ContextualGenerationPipeline,
    GenerationContext,
    GenerationRule,
    GenerationRuleSet,
    RuleRegistry,
    admissibility_constraint_rules,
    combined_generation_rules,
    default_generation_rules,
    default_rule_registry,
    spatial_constraint_rules,
    temporal_constraint_rules,
)
from ometeotl_core.model.actors import Actor

# ---------------------------------------------------------------------------
# GenerationRule / GenerationRuleSet
# ---------------------------------------------------------------------------


def test_generation_rule_applies_when_predicate_is_true():
    rule = GenerationRule(
        name="tag_kind",
        predicate=lambda ctx: ctx.kind == "actor",
        apply=lambda ctx: ctx.copy_with(attributes={**ctx.attributes, "tagged": True}),
    )
    ctx = GenerationContext(kind="actor", id="a-1")
    result = rule.run(ctx)
    assert result.attributes.get("tagged") is True


def test_generation_rule_skips_when_predicate_is_false():
    rule = GenerationRule(
        name="tag_kind",
        predicate=lambda ctx: ctx.kind == "world",
        apply=lambda ctx: ctx.copy_with(attributes={**ctx.attributes, "tagged": True}),
    )
    ctx = GenerationContext(kind="actor", id="a-2")
    result = rule.run(ctx)
    assert "tagged" not in result.attributes


def test_rule_set_applies_rules_in_order():
    calls: list[str] = []

    def make_rule(tag: str) -> GenerationRule:
        return GenerationRule(
            name=f"rule_{tag}",
            predicate=lambda ctx: True,
            apply=lambda ctx, t=tag: (calls.append(t), ctx)[1],
        )

    rule_set = GenerationRuleSet([make_rule("A"), make_rule("B"), make_rule("C")])
    rule_set.apply(GenerationContext(kind="actor", id="x"))
    assert calls == ["A", "B", "C"]


def test_rule_set_exposes_rule_names():
    rule_set = combined_generation_rules()
    names = [r.name for r in rule_set.rules]
    assert "normalize_relations" in names
    assert "promote_label" in names
    assert "propagate_temporal_constraints" in names
    assert "propagate_spatial_constraints" in names
    assert "propagate_admissibility_constraints" in names


# ---------------------------------------------------------------------------
# RuleRegistry
# ---------------------------------------------------------------------------


def test_rule_registry_register_and_get():
    registry = RuleRegistry()
    rule_set = default_generation_rules()
    registry.register("my_rules", rule_set)
    assert registry.exists("my_rules")
    assert registry.get("my_rules") is rule_set


def test_rule_registry_require_raises_on_unknown_name():
    registry = RuleRegistry()
    with pytest.raises(KeyError, match="Unknown generation rule set"):
        registry.require("nonexistent")


def test_rule_registry_register_rejects_empty_name():
    registry = RuleRegistry()
    with pytest.raises(ValueError, match="cannot be empty"):
        registry.register("", default_generation_rules())


def test_rule_registry_names_returns_sorted_list():
    registry = RuleRegistry()
    registry.register("zzz", default_generation_rules())
    registry.register("aaa", temporal_constraint_rules())
    assert registry.names() == ["aaa", "zzz"]


def test_default_rule_registry_contains_all_built_in_rule_sets():
    registry = default_rule_registry()
    assert registry.names() == [
        "admissibility",
        "combined",
        "default",
        "spatial",
        "temporal",
    ]


def test_default_rule_registry_each_built_in_is_a_rule_set():
    registry = default_rule_registry()
    for name in registry.names():
        assert isinstance(registry.require(name), GenerationRuleSet)


# ---------------------------------------------------------------------------
# Temporal constraint propagation
# ---------------------------------------------------------------------------


def test_temporal_constraint_rule_propagates_window_to_metadata():
    rule_set = temporal_constraint_rules()
    ctx = GenerationContext(
        kind="goal",
        id="goal-t-1",
        constraints={"temporal": {"window": 10}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["horizon"]["window"] == 10


def test_temporal_constraint_rule_propagates_start_step_to_metadata():
    rule_set = temporal_constraint_rules()
    ctx = GenerationContext(
        kind="goal",
        id="goal-t-2",
        constraints={"temporal": {"start_step": 5}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["timeline"]["start_step"] == 5


def test_temporal_constraint_rule_coerces_invalid_window_to_fallback():
    rule_set = temporal_constraint_rules()
    ctx = GenerationContext(
        kind="goal",
        id="goal-t-3",
        constraints={"temporal": {"window": -99}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["horizon"]["window"] == 1


def test_temporal_constraint_rule_skips_when_no_temporal_constraints():
    rule_set = temporal_constraint_rules()
    ctx = GenerationContext(kind="goal", id="goal-t-4")
    result = rule_set.apply(ctx)
    assert "horizon" not in result.metadata
    assert "timeline" not in result.metadata


def test_temporal_constraint_rule_does_not_overwrite_existing_metadata():
    rule_set = temporal_constraint_rules()
    ctx = GenerationContext(
        kind="goal",
        id="goal-t-5",
        metadata={"horizon": {"window": 3}},
        constraints={"temporal": {"window": 20}},
    )
    result = rule_set.apply(ctx)
    # pre-existing value preserved (setdefault semantics)
    assert result.metadata["horizon"]["window"] == 3


# ---------------------------------------------------------------------------
# Spatial constraint propagation
# ---------------------------------------------------------------------------


def test_spatial_constraint_rule_propagates_allowed_spaces():
    rule_set = spatial_constraint_rules()
    ctx = GenerationContext(
        kind="actor",
        id="actor-s-1",
        constraints={"spatial": {"allowed_spaces": ["zone-a", "zone-b"]}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["allowed_spaces"] == ["zone-a", "zone-b"]


def test_spatial_constraint_rule_deduplicates_and_sorts_allowed_spaces():
    rule_set = spatial_constraint_rules()
    ctx = GenerationContext(
        kind="actor",
        id="actor-s-2",
        constraints={"spatial": {"allowed_spaces": ["zone-b", "zone-a", "zone-b"]}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["allowed_spaces"] == ["zone-a", "zone-b"]


def test_spatial_constraint_rule_propagates_required_space_to_space_id():
    rule_set = spatial_constraint_rules()
    ctx = GenerationContext(
        kind="action",
        id="action-s-1",
        constraints={"spatial": {"required_space": "zone-c"}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["space_id"] == "zone-c"


def test_spatial_constraint_rule_skips_when_no_spatial_constraints():
    rule_set = spatial_constraint_rules()
    ctx = GenerationContext(kind="actor", id="actor-s-3")
    result = rule_set.apply(ctx)
    assert "allowed_spaces" not in result.metadata
    assert "space_id" not in result.metadata


# ---------------------------------------------------------------------------
# Admissibility constraint propagation
# ---------------------------------------------------------------------------


def test_admissibility_constraint_rule_propagates_required_capability():
    rule_set = admissibility_constraint_rules()
    ctx = GenerationContext(
        kind="goal",
        id="goal-a-1",
        constraints={"admissibility": {"required_capability": "mobility"}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["required_capability"] == "mobility"


def test_admissibility_constraint_rule_propagates_minimum_confidence():
    rule_set = admissibility_constraint_rules()
    ctx = GenerationContext(
        kind="goal",
        id="goal-a-2",
        constraints={"admissibility": {"minimum_confidence": 0.8}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["minimum_confidence"] == pytest.approx(0.8)


def test_admissibility_constraint_rule_clamps_confidence_above_one():
    rule_set = admissibility_constraint_rules()
    ctx = GenerationContext(
        kind="goal",
        id="goal-a-3",
        constraints={"admissibility": {"minimum_confidence": 1.5}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["minimum_confidence"] == pytest.approx(1.0)


def test_admissibility_constraint_rule_clamps_confidence_below_zero():
    rule_set = admissibility_constraint_rules()
    ctx = GenerationContext(
        kind="goal",
        id="goal-a-4",
        constraints={"admissibility": {"minimum_confidence": -0.5}},
    )
    result = rule_set.apply(ctx)
    assert result.metadata["minimum_confidence"] == pytest.approx(0.0)


def test_admissibility_constraint_rule_skips_when_no_admissibility_constraints():
    rule_set = admissibility_constraint_rules()
    ctx = GenerationContext(kind="goal", id="goal-a-5")
    result = rule_set.apply(ctx)
    assert "required_capability" not in result.metadata
    assert "minimum_confidence" not in result.metadata


# ---------------------------------------------------------------------------
# Combined rule set and pipeline integration
# ---------------------------------------------------------------------------


def test_combined_rules_apply_all_propagations_in_one_pass():
    rule_set = combined_generation_rules()
    ctx = GenerationContext(
        kind="actor",
        id="actor-c-1",
        label="Combined Actor",
        relations={"resource": ["res-1", "res-1"]},
        constraints={
            "temporal": {"window": 5},
            "spatial": {"allowed_spaces": ["z1", "z2"]},
            "admissibility": {"minimum_confidence": 0.7},
        },
    )
    result = rule_set.apply(ctx)
    assert result.attributes.get("label") == "Combined Actor"
    assert result.relations["resource"] == ["res-1"]
    assert result.metadata["horizon"]["window"] == 5
    assert result.metadata["allowed_spaces"] == ["z1", "z2"]
    assert result.metadata["minimum_confidence"] == pytest.approx(0.7)


def test_pipeline_uses_combined_rules_and_propagates_spatial_constraint():
    pipeline = ContextualGenerationPipeline()
    ctx = GenerationContext(
        kind="actor",
        id="actor-pipe-1",
        constraints={"spatial": {"allowed_spaces": ["zone-a", "zone-b"]}},
    )
    result = pipeline.generate(ctx)
    assert isinstance(result.generated, Actor)
    assert "propagate_spatial_constraints" in result.applied_rule_names


def test_pipeline_accepts_custom_rule_set_from_registry():
    registry = default_rule_registry()
    pipeline = ContextualGenerationPipeline(rules=registry.require("temporal"))
    ctx = GenerationContext(
        kind="actor",
        id="actor-pipe-2",
        constraints={"temporal": {"window": 7}},
    )
    result = pipeline.generate(ctx)
    assert isinstance(result.generated, Actor)
    assert "propagate_temporal_constraints" in result.applied_rule_names
