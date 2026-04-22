"""Validation layer public API."""

from .base import (
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    VALID_SEVERITIES,
    ValidationContext,
    ValidationException,
    ValidationIssue,
    ValidationResult,
    Validator,
    issue_from_mapping,
)
from .pipeline import (
    MODE_LENIENT,
    MODE_STRICT,
    MODE_WARN_ONLY,
    VALID_PIPELINE_MODES,
    ValidationPipeline,
)
from .policy import (
    PROFILE_ENFORCE_DOMAIN,
    PROFILE_ENFORCE_STRUCTURE,
    PROFILE_HARDEN_CORE,
    PROFILE_HARDEN_STRUCTURAL,
    PROFILE_OBSERVE_ONLY,
    PROFILE_SOFT_GATE,
    VALID_POLICY_PROFILES,
    build_stage_modes,
)
from .syntactic import SyntacticValidator
from .structural import StructuralValidator
from .temporal import TemporalValidator
from .spatial import SpatialValidator
from .admissibility import AdmissibilityValidator
from .epistemic import EpistemicValidator
from .completeness import (
    LEVEL_FULL,
    LEVEL_MINIMAL,
    LEVEL_RECOMMENDED,
    CompletenessValidator,
)
from .diagnostic import DiagnosticBuilder, DiagnosticEntry, DiagnosticReport

__all__ = [
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    "VALID_SEVERITIES",
    "ValidationIssue",
    "ValidationContext",
    "ValidationResult",
    "ValidationException",
    "Validator",
    "issue_from_mapping",
    "MODE_STRICT",
    "MODE_LENIENT",
    "MODE_WARN_ONLY",
    "VALID_PIPELINE_MODES",
    "ValidationPipeline",
    "PROFILE_OBSERVE_ONLY",
    "PROFILE_ENFORCE_STRUCTURE",
    "PROFILE_ENFORCE_DOMAIN",
    "PROFILE_SOFT_GATE",
    "PROFILE_HARDEN_STRUCTURAL",
    "PROFILE_HARDEN_CORE",
    "VALID_POLICY_PROFILES",
    "build_stage_modes",
    "SyntacticValidator",
    "StructuralValidator",
    "TemporalValidator",
    "SpatialValidator",
    "AdmissibilityValidator",
    "EpistemicValidator",
    "CompletenessValidator",
    "LEVEL_MINIMAL",
    "LEVEL_RECOMMENDED",
    "LEVEL_FULL",
    "DiagnosticBuilder",
    "DiagnosticEntry",
    "DiagnosticReport",
]
