"""Validation policy profiles for progressive hardening rollout.

Policy profiles:
- ``observe_only``: run validators in warn-only mode unless explicitly
    overridden per stage.
- ``enforce_structure``: enforce syntactic, structural, and completeness
    stages as strict errors.
- ``enforce_domain``: enforce both structure and domain semantics
    (temporal/spatial/admissibility/epistemic) as strict errors.
"""

from __future__ import annotations

from typing import Mapping

from .pipeline import (
    MODE_STRICT,
    MODE_WARN_ONLY,
    VALID_PIPELINE_MODES,
)

PROFILE_OBSERVE_ONLY = "observe_only"
PROFILE_ENFORCE_STRUCTURE = "enforce_structure"
PROFILE_ENFORCE_DOMAIN = "enforce_domain"

VALID_POLICY_PROFILES: frozenset[str] = frozenset(
    {
        PROFILE_OBSERVE_ONLY,
        PROFILE_ENFORCE_STRUCTURE,
        PROFILE_ENFORCE_DOMAIN,
    }
)


def build_stage_modes(
    *,
    policy_profile: str = PROFILE_OBSERVE_ONLY,
    stage_mode_overrides: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return stage-mode mapping for the chosen profile and explicit overrides.

    Args:
        policy_profile: Validation hardening profile name.
            - ``observe_only`` keeps non-blocking defaults.
            - ``enforce_structure`` promotes core schema checks to strict.
            - ``enforce_domain`` additionally promotes domain checks to strict.
        stage_mode_overrides: Per-stage mode overrides, where values must be
            one of ``strict``, ``lenient``, or ``warn_only``.
    """
    if policy_profile not in VALID_POLICY_PROFILES:
        raise ValueError(
            f"Unsupported validation policy profile: {policy_profile}. "
            f"Expected one of {sorted(VALID_POLICY_PROFILES)}"
        )

    stage_modes: dict[str, str] = {}
    if policy_profile == PROFILE_ENFORCE_STRUCTURE:
        stage_modes.update(
            {
                "syntactic": MODE_STRICT,
                "structural": MODE_STRICT,
                "completeness": MODE_STRICT,
            }
        )
    elif policy_profile == PROFILE_ENFORCE_DOMAIN:
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

    for stage_name, mode in dict(
        stage_mode_overrides or {}
    ).items():
        normalized_mode = str(mode or MODE_WARN_ONLY)
        if normalized_mode not in VALID_PIPELINE_MODES:
            raise ValueError(
                f"Unsupported validation mode override '{normalized_mode}' "
                f"for stage '{stage_name}'"
            )
        stage_modes[str(stage_name)] = normalized_mode

    return stage_modes
