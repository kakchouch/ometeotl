"""Tests for contextual generation pipeline."""

from typing import Any, cast

import pytest

from tests.ometeotl_core._artifact_utils import write_json_artifact

from ometeotl_core.generation import (
    ContextualGenerationPipeline,
    GenerationContext,
    GenerationPlacement,
)
from ometeotl_core.model.actions import Action
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.resources import Resource
from ometeotl_core.model.spaces import Space
from ometeotl_core.model.strategies import Strategy
from ometeotl_core.model.world import World
from ometeotl_core.validation import (
    SEVERITY_ERROR,
    ValidationContext,
    ValidationIssue,
    ValidationPipeline,
    ValidationResult,
)


class _AlwaysPassValidator:
    @property
    def name(self) -> str:
        return "always_pass"

    def validate(self, obj, context: ValidationContext) -> ValidationResult:
        return ValidationResult(stage=context.stage, policy_mode=context.policy_mode)


class _AlwaysFailValidator:
    @property
    def name(self) -> str:
        return "always_fail"

    def validate(self, obj, context: ValidationContext) -> ValidationResult:
        return ValidationResult(
            stage=context.stage,
            policy_mode=context.policy_mode,
            issues=[
                ValidationIssue(
                    code="GEN-FAIL",
                    severity=SEVERITY_ERROR,
                    message="Synthetic validation failure for pipeline testing",
                    object_id=str(getattr(obj, "id", "")),
                )
            ],
        )


def test_pipeline_generates_world_with_registered_objects_and_placements():
    pipeline = ContextualGenerationPipeline()
    world_context = GenerationContext(
        kind="world",
        id="world-gen-1",
        label="Generated World",
        spaces=[GenerationContext(kind="space", id="zone-a")],
        actors=[GenerationContext(kind="actor", id="actor-a", label="Alice")],
        resources=[GenerationContext(kind="resource", id="resource-a")],
        placements=[GenerationPlacement(object_id="actor-a", space_id="zone-a")],
    )

    result = pipeline.generate(world_context)

    assert isinstance(result.generated, World)
    assert result.generated.get_space("zone-a") is not None
    assert result.generated.model_registry.get("actor-a") is not None
    assert result.generated.model_registry.get("resource-a") is not None
    assert "actor-a" in result.generated.space_object_graph.list_objects_in_space(
        "zone-a"
    )


def test_pipeline_generates_actor_with_label_promoted_to_attributes():
    pipeline = ContextualGenerationPipeline()
    actor_context = GenerationContext(
        kind="actor", id="actor-gen-1", label="Generated Actor"
    )

    result = pipeline.generate(actor_context)

    assert isinstance(result.generated, Actor)
    assert result.generated.label == "Generated Actor"


def test_pipeline_generates_goal_from_metadata():
    pipeline = ContextualGenerationPipeline()
    goal_context = GenerationContext(
        kind="goal",
        id="goal-gen-1",
        metadata={
            "actor_id": "actor-1",
            "kind": "final",
            "priority": 0.7,
            "status": "active",
            "target_condition": {"state": "safe"},
        },
    )

    result = pipeline.generate(goal_context)

    assert isinstance(result.generated, Goal)
    assert result.generated.actor_id == "actor-1"
    assert result.generated.priority == 0.7
    assert result.generated.target_condition == {"state": "safe"}


def test_pipeline_generates_goal_preserving_zero_priority():
    pipeline = ContextualGenerationPipeline()
    goal_context = GenerationContext(
        kind="goal",
        id="goal-gen-priority-zero",
        metadata={
            "actor_id": "actor-1",
            "kind": "intermediate",
            "priority": 0.0,
        },
    )

    result = pipeline.generate(goal_context)

    assert isinstance(result.generated, Goal)
    assert result.generated.priority == 0.0


def test_pipeline_generates_strategy_with_default_single_node():
    pipeline = ContextualGenerationPipeline()
    strategy_context = GenerationContext(
        kind="strategy",
        id="strategy-gen-1",
        metadata={
            "actor_id": "actor-1",
            "goal_id": "goal-1",
            "root_node_id": "node-root",
            "action_id": "action-1",
        },
    )

    result = pipeline.generate(strategy_context)

    assert isinstance(result.generated, Strategy)
    assert result.generated.actor_id == "actor-1"
    assert result.generated.root_node_id == "node-root"
    assert len(result.generated.nodes) == 1
    assert result.generated.nodes[0].action_id == "action-1"


def test_pipeline_generates_action_from_metadata():
    pipeline = ContextualGenerationPipeline()
    action_context = GenerationContext(
        kind="action",
        id="action-gen-1",
        metadata={
            "actor_id": "actor-1",
            "world_id": "world-1",
            "space_id": "zone-a",
            "action_type": "move",
        },
    )

    result = pipeline.generate(action_context)

    assert isinstance(result.generated, Action)
    assert result.generated.actor_id == "actor-1"
    assert result.generated.world_id == "world-1"
    assert result.generated.space_id == "zone-a"
    assert result.generated.action_type == "move"


def test_pipeline_generates_perception_from_context_metadata():
    pipeline = ContextualGenerationPipeline()
    perception_context = GenerationContext(
        kind="perception",
        id="perception-gen-1",
        metadata={
            "actor_id": "actor-1",
            "source_id": "world-1",
            "timestamp": 42,
            "perceived_spaces": {
                "zone-a": {
                    "space": {"id": "zone-a", "object_type": "space"},
                    "epistemic_status": "certain",
                }
            },
            "perceived_memberships": [
                {
                    "membership": {
                        "object_id": "actor-1",
                        "space_id": "zone-a",
                        "role": "occupies",
                    },
                    "epistemic_status": "believed",
                }
            ],
            "perceived_relations": [
                {
                    "relation": {
                        "source_space_id": "zone-a",
                        "target_space_id": "zone-b",
                        "relation_type": "adjacent_to",
                    },
                    "epistemic_status": "hypothesis",
                }
            ],
            "perceived_component_links": [
                {
                    "link_id": "link-1",
                    "composite_id": "actor-1",
                    "component_id": "actor-2",
                    "epistemic_status": "projected",
                }
            ],
        },
    )

    result = pipeline.generate(perception_context)

    assert isinstance(result.generated, Perception)
    assert result.generated.actor_id == "actor-1"
    assert result.generated.source_id == "world-1"
    assert result.generated.timestamp == 42
    assert sorted(result.generated.perceived_spaces.keys()) == ["zone-a"]
    assert len(result.generated.perceived_memberships) == 1
    assert len(result.generated.perceived_relations) == 1
    assert len(result.generated.perceived_component_links) == 1


def test_generation_audit_writes_local_lab_artifact():
    """Write a stable generation snapshot under local_lab for audit review."""
    pipeline = ContextualGenerationPipeline()

    generated_world = pipeline.generate(
        GenerationContext(
            kind="world",
            id="world-audit-1",
            spaces=[GenerationContext(kind="space", id="zone-a")],
            actors=[GenerationContext(kind="actor", id="actor-a", label="Alice")],
            resources=[GenerationContext(kind="resource", id="resource-a")],
            placements=[GenerationPlacement(object_id="actor-a", space_id="zone-a")],
        )
    ).generated
    generated_strategy = pipeline.generate(
        GenerationContext(
            kind="strategy",
            id="strategy-audit-1",
            metadata={
                "actor_id": "actor-a",
                "goal_id": "goal-a",
                "root_node_id": "node-root",
                "action_id": "action-a",
            },
        )
    ).generated
    generated_perception = pipeline.generate(
        GenerationContext(
            kind="perception",
            id="perception-audit-1",
            metadata={
                "actor_id": "actor-a",
                "source_id": "world-audit-1",
                "perceived_spaces": {
                    "zone-a": {
                        "space": {"id": "zone-a", "object_type": "space"},
                        "epistemic_status": "certain",
                    }
                },
            },
        )
    ).generated

    payload = {
        "world": generated_world.to_dict(),
        "strategy": generated_strategy.to_dict(),
        "perception": generated_perception.to_dict(),
    }
    artifact_path = write_json_artifact(
        layer="generation",
        name="generation_snapshot",
        payload=payload,
    )

    assert artifact_path.name == "generation_snapshot.json"


def test_pipeline_validation_requested_without_pipeline_records_diagnostic():
    pipeline = ContextualGenerationPipeline()
    actor_context = GenerationContext(
        kind="actor",
        id="actor-validate-missing-pipeline",
        validate=True,
    )

    result = pipeline.generate(actor_context)

    assert result.validation is None
    assert any(
        "Validation requested but no validation pipeline is configured" in item
        for item in result.diagnostics
    )


def test_pipeline_validation_success_with_configured_pipeline():
    pipeline = ContextualGenerationPipeline(
        validation_pipeline=ValidationPipeline(validators=[_AlwaysPassValidator()])
    )
    actor_context = GenerationContext(
        kind="actor",
        id="actor-validate-pass",
        validate=True,
    )

    result = pipeline.generate(actor_context)

    assert result.validation is not None
    assert result.validation.valid is True
    assert result.validation.metadata["executed_validators"] == ["always_pass"]
    assert not any("failed validation" in item for item in result.diagnostics)


def test_pipeline_validation_failure_emits_diagnostic_and_result():
    pipeline = ContextualGenerationPipeline(
        validation_pipeline=ValidationPipeline(validators=[_AlwaysFailValidator()])
    )
    actor_context = GenerationContext(
        kind="actor",
        id="actor-validate-fail",
        validate=True,
    )

    result = pipeline.generate(actor_context)

    assert result.validation is not None
    assert result.validation.valid is False
    assert result.validation.summary["error"] == 1
    assert any("failed validation" in item for item in result.diagnostics)


def test_pipeline_registers_generated_goal_when_world_context_is_required():
    pipeline = ContextualGenerationPipeline()
    world = World(id="world-registry-1")
    world.register_object(Actor(id="actor-1"))

    goal_context = GenerationContext(
        kind="goal",
        id="goal-registered-1",
        registration_policy="require",
        metadata={
            "actor_id": "actor-1",
            "kind": "final",
            "target_condition": {"state": "safe"},
        },
    )

    result = pipeline.generate(goal_context, world=world)

    assert world.model_registry.get("goal-registered-1") is result.generated
    assert any("Registered generated goal" in item for item in result.diagnostics)


def test_pipeline_registers_generated_strategy_and_action_when_world_available():
    pipeline = ContextualGenerationPipeline()
    world = World(id="world-registry-2")
    world.add_space(Space(id="zone-a"))

    strategy_result = pipeline.generate(
        GenerationContext(
            kind="strategy",
            id="strategy-registered-1",
            registration_policy="if_available",
            metadata={
                "actor_id": "actor-1",
                "goal_id": "goal-1",
                "action_id": "action-1",
            },
        ),
        world=world,
    )
    action_result = pipeline.generate(
        GenerationContext(
            kind="action",
            id="action-registered-1",
            registration_policy="if_available",
            metadata={
                "actor_id": "actor-1",
                "world_id": world.id,
                "space_id": "zone-a",
                "action_type": "move",
            },
        ),
        world=world,
    )

    assert (
        world.model_registry.get("strategy-registered-1") is strategy_result.generated
    )
    assert world.model_registry.get("action-registered-1") is action_result.generated


def test_pipeline_registers_generated_actor_and_resource_when_world_available():
    pipeline = ContextualGenerationPipeline()
    world = World(id="world-registry-actor-resource")

    actor_result = pipeline.generate(
        GenerationContext(
            kind="actor",
            id="actor-registered-policy",
            registration_policy="if_available",
        ),
        world=world,
    )
    resource_result = pipeline.generate(
        GenerationContext(
            kind="resource",
            id="resource-registered-policy",
            registration_policy="if_available",
        ),
        world=world,
    )

    assert isinstance(actor_result.generated, Actor)
    assert isinstance(resource_result.generated, Resource)
    assert world.model_registry.get("actor-registered-policy") is actor_result.generated
    assert (
        world.model_registry.get("resource-registered-policy")
        is resource_result.generated
    )


def test_pipeline_registration_policy_require_without_world_raises():
    pipeline = ContextualGenerationPipeline()

    with pytest.raises(ValueError):
        pipeline.generate(
            GenerationContext(
                kind="goal",
                id="goal-missing-world",
                registration_policy="require",
                metadata={"actor_id": "actor-1", "kind": "final"},
            )
        )


def test_pipeline_registration_policy_require_rejects_non_model_generated(monkeypatch):
    import ometeotl_core.generation.pipeline as pipeline_module

    pipeline = ContextualGenerationPipeline()
    world = World(id="world-registry-non-model-require")
    world.register_object(Actor(id="actor-1"))

    def _fake_build(_context: GenerationContext):
        return {"id": "not-a-model-object"}

    monkeypatch.setattr(pipeline_module, "build_from_context", _fake_build)

    with pytest.raises(TypeError, match="Registration policy 'require' failed"):
        pipeline.generate(
            GenerationContext(
                kind="goal",
                id="goal-non-model-require",
                registration_policy="require",
                metadata={"actor_id": "actor-1", "kind": "final"},
            ),
            world=world,
        )


def test_pipeline_registration_if_available_without_world_adds_diagnostic():
    pipeline = ContextualGenerationPipeline()
    result = pipeline.generate(
        GenerationContext(
            kind="goal",
            id="goal-skip-world",
            registration_policy="if_available",
            metadata={"actor_id": "actor-1", "kind": "final"},
        )
    )

    assert any("Skipped registration" in item for item in result.diagnostics)


def test_pipeline_partial_update_merges_attributes_state_and_relations():
    pipeline = ContextualGenerationPipeline()
    world = World(id="world-update-1")
    actor = Actor(id="actor-update-1")
    actor.set_attribute("existing", "value")
    actor.add_relation("resource", "resource-a")
    world.register_object(actor)

    result = pipeline.generate(
        GenerationContext(
            kind="actor",
            id="actor-update-1",
            operation="partial_update",
            attributes={"new": "value"},
            state={"mood": "focused"},
            relations={"resource": ["resource-b"]},
        ),
        world=world,
    )

    assert result.generated is actor
    assert actor.attributes["existing"] == "value"
    assert actor.attributes["new"] == "value"
    assert actor.state["mood"] == "focused"
    assert actor.relations["resource"] == ["resource-a", "resource-b"]


def test_pipeline_corrective_update_replaces_specified_relations():
    pipeline = ContextualGenerationPipeline()
    world = World(id="world-update-2")
    actor = Actor(id="actor-update-2")
    actor.add_relation("resource", "resource-a")
    actor.add_relation("resource", "resource-b")
    world.register_object(actor)

    result = pipeline.generate(
        GenerationContext(
            kind="actor",
            id="actor-update-2",
            operation="corrective_update",
            relations={"resource": ["resource-c"]},
        ),
        world=world,
    )

    assert result.generated is actor
    assert actor.relations["resource"] == ["resource-c"]


def test_pipeline_partial_update_preserves_falsy_non_string_context_keys():
    pipeline = ContextualGenerationPipeline()
    world = World(id="world-update-falsy-keys")
    actor_zero = Actor(id="actor-update-falsy-key-zero")
    actor_false = Actor(id="actor-update-falsy-key-false")
    world.register_object(actor_zero)
    world.register_object(actor_false)

    zero_result = pipeline.generate(
        GenerationContext(
            kind="actor",
            id="actor-update-falsy-key-zero",
            operation="partial_update",
            context=cast(dict[str, Any], {0: "zero-key", "": "ignored-empty"}),
        ),
        world=world,
    )

    false_result = pipeline.generate(
        GenerationContext(
            kind="actor",
            id="actor-update-falsy-key-false",
            operation="partial_update",
            context=cast(dict[str, Any], {False: "false-key"}),
        ),
        world=world,
    )

    assert zero_result.generated is actor_zero
    assert false_result.generated is actor_false
    assert cast(dict[Any, Any], actor_zero.context)[0] == "zero-key"
    assert "" not in actor_zero.context
    assert cast(dict[Any, Any], actor_false.context)[False] == "false-key"


def test_pipeline_partial_update_context_is_blocked_by_authority_mode():
    pipeline = ContextualGenerationPipeline()
    world = World(id="world-update-authority-1")
    actor = Actor(id="actor-update-authority-1")
    world.register_object(actor)
    world.enable_authority_mode("secret")

    with pytest.raises(PermissionError):
        pipeline.generate(
            GenerationContext(
                kind="actor",
                id="actor-update-authority-1",
                operation="partial_update",
                context={"risk": "high"},
            ),
            world=world,
        )


def test_pipeline_corrective_update_context_is_blocked_by_authority_mode():
    pipeline = ContextualGenerationPipeline()
    world = World(id="world-update-authority-2")
    actor = Actor(id="actor-update-authority-2")
    world.register_object(actor)
    world.enable_authority_mode("secret")

    with pytest.raises(PermissionError):
        pipeline.generate(
            GenerationContext(
                kind="actor",
                id="actor-update-authority-2",
                operation="corrective_update",
                context={"risk": "high"},
            ),
            world=world,
        )


def test_pipeline_update_operation_requires_existing_target():
    pipeline = ContextualGenerationPipeline()
    world = World(id="world-update-3")

    with pytest.raises(ValueError):
        pipeline.generate(
            GenerationContext(
                kind="actor",
                id="missing-actor",
                operation="partial_update",
                attributes={"new": "value"},
            ),
            world=world,
        )


def test_pipeline_perception_generation_rejects_component_link_missing_link_id():
    pipeline = ContextualGenerationPipeline()

    with pytest.raises(ValueError):
        pipeline.generate(
            GenerationContext(
                kind="perception",
                id="perception-invalid-link-id",
                metadata={
                    "actor_id": "actor-1",
                    "source_id": "world-1",
                    "perceived_component_links": [
                        {
                            "composite_id": "actor-1",
                            "component_id": "actor-2",
                            "epistemic_status": "projected",
                        }
                    ],
                },
            )
        )


def test_pipeline_perception_generation_rejects_component_link_missing_component_id():
    pipeline = ContextualGenerationPipeline()

    with pytest.raises(ValueError):
        pipeline.generate(
            GenerationContext(
                kind="perception",
                id="perception-invalid-component-id",
                metadata={
                    "actor_id": "actor-1",
                    "source_id": "world-1",
                    "perceived_component_links": [
                        {
                            "link_id": "link-1",
                            "composite_id": "actor-1",
                            "epistemic_status": "projected",
                        }
                    ],
                },
            )
        )


def test_pipeline_perception_generation_rejects_membership_missing_payload():
    pipeline = ContextualGenerationPipeline()

    with pytest.raises(ValueError, match="requires 'membership' payload"):
        pipeline.generate(
            GenerationContext(
                kind="perception",
                id="perception-invalid-membership-missing",
                metadata={
                    "actor_id": "actor-1",
                    "source_id": "world-1",
                    "perceived_memberships": [
                        {
                            "epistemic_status": "certain",
                        }
                    ],
                },
            )
        )


def test_pipeline_perception_generation_rejects_membership_empty_mapping():
    pipeline = ContextualGenerationPipeline()

    with pytest.raises(ValueError, match="requires non-empty 'membership' mapping"):
        pipeline.generate(
            GenerationContext(
                kind="perception",
                id="perception-invalid-membership-empty",
                metadata={
                    "actor_id": "actor-1",
                    "source_id": "world-1",
                    "perceived_memberships": [
                        {
                            "membership": {},
                            "epistemic_status": "certain",
                        }
                    ],
                },
            )
        )
