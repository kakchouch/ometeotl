"""Tests for masm.validation.completeness."""

from masm.validation.base import ValidationContext
from masm.validation.completeness import (
    LEVEL_FULL,
    LEVEL_MINIMAL,
    LEVEL_RECOMMENDED,
    CompletenessValidator,
)


def test_completeness_validator_rejects_missing_required_fields():
    """Minimal completeness must fail on missing required fields."""
    payload = {"object_type": "action", "actor_id": "a-1"}

    result = CompletenessValidator().validate(
        payload,
        ValidationContext(metadata={"completeness_level": LEVEL_MINIMAL}),
    )

    assert result.valid is False
    assert any(issue.code == "COMP-MISSING-REQUIRED" for issue in result.errors)


def test_completeness_validator_warns_missing_recommended_fields():
    """Recommended level reports missing recommended fields as warnings."""
    payload = {
        "id": "goal-1",
        "object_type": "goal",
        "schema_version": "1.0",
        "actor_id": "actor-1",
        "kind": "final",
    }

    result = CompletenessValidator().validate(
        payload,
        ValidationContext(metadata={"completeness_level": LEVEL_RECOMMENDED}),
    )

    assert result.valid is True
    assert any(issue.code == "COMP-MISSING-RECOMMENDED" for issue in result.warnings)


def test_completeness_validator_full_level_promotes_recommended_to_error():
    """Full completeness treats missing recommended fields as errors."""
    payload = {
        "id": "strategy-1",
        "object_type": "strategy",
        "schema_version": "1.0",
        "actor_id": "actor-1",
        "root_node_id": "node-1",
    }

    result = CompletenessValidator().validate(
        payload,
        ValidationContext(metadata={"completeness_level": LEVEL_FULL}),
    )

    assert result.valid is False
    assert any(issue.code == "COMP-MISSING-RECOMMENDED" for issue in result.errors)
