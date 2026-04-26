"""Tests for ometeotl_core.validation.structural."""

from ometeotl_core.model.goals import Goal, GoalDecompositionTree
from ometeotl_core.validation.base import ValidationContext
from ometeotl_core.validation.structural import StructuralValidator


def test_structural_validator_accepts_minimal_model_payload():
    """A minimal canonical payload should pass structural checks."""
    validator = StructuralValidator()
    payload = {
        "id": "obj-1",
        "object_type": "generic",
        "schema_version": "1.0",
        "attributes": {},
        "relations": {"linked": ["obj-2"]},
        "state": {},
        "context": {},
        "provenance": {},
    }

    result = validator.validate(payload, ValidationContext())

    assert result.valid is True


def test_structural_validator_rejects_missing_identity_fields():
    """Missing id/object_type should be flagged as structural errors."""
    validator = StructuralValidator()

    result = validator.validate(
        {"schema_version": "1.0"}, ValidationContext()
    )

    assert result.valid is False
    assert result.summary["error"] >= 2


def test_structural_validator_rejects_invalid_relations_shape():
    """relations entries must contain sequence values with string IDs."""
    validator = StructuralValidator()
    payload = {
        "id": "obj-2",
        "object_type": "generic",
        "schema_version": "1.0",
        "relations": {
            "invalid": "not-a-list",
            "mixed": ["obj-1", "", 3],
        },
    }

    result = validator.validate(payload, ValidationContext())

    assert result.valid is False
    codes = {issue.code for issue in result.errors}
    assert "STR-RELATION-TARGETS-TYPE" in codes
    assert "STR-RELATION-TARGET-ID" in codes


def test_structural_validator_reuses_strategy_tree_validation():
    """Strategy payloads should reuse existing strategy.validate_tree logic."""
    validator = StructuralValidator()
    payload = {
        "id": "strategy-1",
        "object_type": "strategy",
        "schema_version": "1.0",
        "attributes": {},
        "relations": {},
        "state": {},
        "context": {},
        "provenance": {},
        "actor_id": "actor-1",
        "root_node_id": "node-a",
        "nodes": [
            {
                "node_id": "node-a",
                "action_id": "action-1",
                "source_perception_id": None,
                "projected_state": None,
                "outcome_branches": [
                    {
                        "branch_id": "b1",
                        "child_node_id": "node-missing",
                        "label": "failure",
                        "probability": None,
                        "condition": {},
                        "metadata": {},
                    }
                ],
                "metadata": {},
            }
        ],
        "projection_policy": "perception_first",
    }

    result = validator.validate(payload, ValidationContext())

    assert result.valid is False
    assert any(
        issue.code == "STR-STRATEGY-TREE"
        for issue in result.errors
    )


def test_structural_validator_reuses_goal_tree_validation():
    """Goal tree instances should use existing GoalDecompositionTree.validate_tree."""
    validator = StructuralValidator()
    goal_a = Goal(
        id="goal-a",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        child_goal_ids=["goal-b"],
    )
    goal_b = Goal(
        id="goal-b",
        actor_id="actor-1",
        kind="intermediate",
        target_condition={},
        parent_goal_id="goal-a",
        child_goal_ids=["goal-a"],
    )
    tree = GoalDecompositionTree(
        root_goal_id="goal-a",
        goals={"goal-a": goal_a, "goal-b": goal_b},
    )

    result = validator.validate(tree, ValidationContext())

    assert result.valid is False
    assert any(
        issue.code == "STR-GOAL-TREE" for issue in result.errors
    )
