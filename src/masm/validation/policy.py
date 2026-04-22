"""Validation policy profiles for progressive hardening rollout."""

from __future__ import annotations

from typing import Mapping

from .pipeline import MODE_STRICT, MODE_WARN_ONLY, VALID_PIPELINE_MODES

PROFILE_SOFT_GATE = "soft_gate"
PROFILE_HARDEN_STRUCTURAL = "harden_structural"
PROFILE_HARDEN_CORE = "harden_core"

VALID_POLICY_PROFILES: frozenset[str] = frozenset(
    {PROFILE_SOFT_GATE, PROFILE_HARDEN_STRUCTURAL, PROFILE_HARDEN_CORE}
)


def build_stage_modes(
    *,
    policy_profile: str = PROFILE_SOFT_GATE,
    stage_mode_overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return stage-mode mapping for the chosen profile and explicit overrides."""
    if policy_profile not in VALID_POLICY_PROFILES:
        raise ValueError(
            f"Unsupported validation policy profile: {policy_profile}. "
            f"Expected one of {sorted(VALID_POLICY_PROFILES)}"
        )

    stage_modes: dict[str, str] = {}
    if policy_profile == PROFILE_HARDEN_STRUCTURAL:
        stage_modes.update(
            {
                "syntactic": MODE_STRICT,
                "structural": MODE_STRICT,
                "completeness": MODE_STRICT,
            }
        )
    elif policy_profile == PROFILE_HARDEN_CORE:
        stage_modes.update(
            {
                "syntactic": MODE_STRICT,
                "structural": MODE_STRICT,
                "completeness": MODE_STRICT,
                "temporal": MODE_STRICT,
                "spatial": MODE_STRICT,
                "admissibility": MODE_STRICT,
                "epistemic": MODE_STRICT,
            }
        )

    for stage_name, mode in dict(stage_mode_overrides or {}).items():
        normalized_mode = str(mode or MODE_WARN_ONLY)
        if normalized_mode not in VALID_PIPELINE_MODES:
            raise ValueError(
                f"Unsupported validation mode override '{normalized_mode}' "
                f"for stage '{stage_name}'"
            )
        stage_modes[str(stage_name)] = normalized_mode

    return stage_modes
