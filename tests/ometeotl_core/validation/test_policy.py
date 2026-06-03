"""Tests for ometeotl_core.validation.policy."""

import pytest

from ometeotl_core.validation import (
    MODE_STRICT,
    PROFILE_ENFORCE_DOMAIN,
    PROFILE_ENFORCE_STRUCTURE,
    PROFILE_OBSERVE_ONLY,
    build_stage_modes,
)


def test_observe_only_profile_defaults_to_no_stage_overrides():
    """Observe-only profile keeps warn-only behavior through empty overrides."""
    assert build_stage_modes(policy_profile=PROFILE_OBSERVE_ONLY) == {}


def test_enforce_structure_profile_promotes_expected_stages():
    """Enforce-structure profile promotes core schema stages to strict."""
    stage_modes = build_stage_modes(policy_profile=PROFILE_ENFORCE_STRUCTURE)

    assert stage_modes["syntactic"] == MODE_STRICT
    assert stage_modes["structural"] == MODE_STRICT
    assert stage_modes["completeness"] == MODE_STRICT


def test_enforce_domain_profile_promotes_temporal_and_spatial_checks():
    """Enforce-domain profile also promotes dynamic domain validator stages."""
    stage_modes = build_stage_modes(policy_profile=PROFILE_ENFORCE_DOMAIN)

    assert stage_modes["temporal"] == MODE_STRICT
    assert stage_modes["spatial"] == MODE_STRICT
    assert stage_modes["admissibility"] == MODE_STRICT
    assert stage_modes["epistemic"] == MODE_STRICT


def test_stage_mode_overrides_take_precedence_over_profile_defaults():
    """Explicit stage overrides should win over profile-provided defaults."""
    stage_modes = build_stage_modes(
        policy_profile=PROFILE_ENFORCE_STRUCTURE,
        stage_mode_overrides={"structural": "lenient"},
    )

    assert stage_modes["structural"] == "lenient"


def test_unknown_policy_profile_raises_value_error():
    """Invalid policy profile names are rejected eagerly."""
    with pytest.raises(ValueError):
        build_stage_modes(policy_profile="unknown-profile")
