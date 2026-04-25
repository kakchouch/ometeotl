"""Utility function model primitives.

This module defines the abstract UtilityFunction interface (F-26) enabling
domain-specific evaluation of actions, strategies, and goals relative to an
actor's perceived state and an interpretive framework (A-22, G-6).

A utility function maps a perception state and an actor to a scalar or vector
of utility values, without imposing any concrete objective. The framework
remains teleologically neutral while providing structure for domain-specific
utility derivation.

This module is intentionally declarative. Execution, ranking, and aggregation
remain out of scope for this iteration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Union

from .actors import Actor
from .base import (
    JsonMap,
    _canonical_json_map,
    _require_non_empty,
)
from .perception import Perception


@dataclass
class UtilityFrame:
    """Container for a utility evaluation result.

    A utility frame wraps the output of a UtilityFunction, including the value(s),
    interpretive framework reference, and optional multi-criteria metadata.
    """

    value: Union[float, list[float]]
    framework_id: str
    criteria_labels: list[str] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(
            self.framework_id,
            "UtilityFrame framework_id cannot be empty",
        )
        if isinstance(self.value, list):
            if self.criteria_labels and len(
                self.criteria_labels
            ) != len(self.value):
                raise ValueError(
                    "UtilityFrame criteria_labels length must match value list length"
                )

    @property
    def is_multi_criteria(self) -> bool:
        """Return True if value is a vector (multi-criteria utility)."""
        return isinstance(self.value, list)

    @property
    def scalar_value(self) -> float:
        """Return the value as a scalar. Raises if value is a vector."""
        if isinstance(self.value, list):
            raise ValueError(
                "Cannot extract scalar_value from multi-criteria utility; use value instead"
            )
        return self.value

    def to_dict(self) -> JsonMap:
        """Serialize the utility frame."""
        return {
            "value": (
                self.value
                if not isinstance(self.value, list)
                else list(self.value)
            ),
            "framework_id": self.framework_id,
            "criteria_labels": list(self.criteria_labels),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any]
    ) -> "UtilityFrame":
        """Reconstruct a utility frame from mapping data."""
        raw_value = data.get("value")
        if isinstance(raw_value, list):
            value: Union[float, list[float]] = [
                float(v) for v in raw_value
            ]
        else:
            value = (
                float(raw_value)
                if raw_value is not None
                else 0.0
            )

        return cls(
            value=value,
            framework_id=str(data.get("framework_id") or ""),
            criteria_labels=[
                str(label)
                for label in (data.get("criteria_labels") or [])
            ],
            metadata=dict(data.get("metadata") or {}),
        )


class UtilityFunction(ABC):
    """Abstract base class for utility functions.

    A utility function evaluates the utility of a perceived state for an actor
    relative to an interpretive framework (A-22). Utility is domain-specific and
    framework-dependent; this interface imposes no concrete objectives (P-1, A-23).

    Core specs addressed: A-22 (interpretive framework), G-6 (multi-criteria utility).

    Policy contract for ``resolve_numeric_metrics``:
    - supported policy names (stable enum):
      - ``default_neutral``: missing metrics fall back to ``0.0``
      - ``default_pessimistic``: missing metrics fall back to a negative value
    - fallback precedence and resolution order are deterministic and documented
      in the helper docstring.
    """

    MISSING_METRIC_POLICY_DEFAULT_NEUTRAL = "default_neutral"
    MISSING_METRIC_POLICY_DEFAULT_PESSIMISTIC = (
        "default_pessimistic"
    )
    SUPPORTED_MISSING_METRIC_POLICIES = {
        MISSING_METRIC_POLICY_DEFAULT_NEUTRAL,
        MISSING_METRIC_POLICY_DEFAULT_PESSIMISTIC,
    }

    @property
    @abstractmethod
    def framework_id(self) -> str:
        """Identifier of the interpretive framework this utility function uses."""

    @property
    @abstractmethod
    def is_multi_criteria(self) -> bool:
        """Return True if this function produces vector-valued utilities (G-6)."""

    @abstractmethod
    def evaluate(
        self,
        perception: Perception,
        actor: Actor,
        context: JsonMap,
    ) -> UtilityFrame:
        """Evaluate utility of a perceived state for an actor."""

    def resolve_numeric_metrics(
        self,
        metric_keys: list[str],
        *,
        perception: Perception,
        context: JsonMap,
    ) -> tuple[dict[str, float], JsonMap]:
        """Resolve numeric metrics with a deterministic fallback policy.

        Policy configuration keys in ``context``:
        - ``missing_metric_policy``:
          - ``"default_neutral"`` (preferred default)
          - ``"default_pessimistic"``
        - ``missing_metric_default``: explicit numeric fallback override.
        - ``missing_metric_strict_invalid``: when ``True``, invalid present values
          raise ``ValueError`` instead of falling back.
        - ``fallback_dominance_threshold``: ratio in ``[0, 1]`` used to flag when
          fallback usage dominates a metric vector (default ``0.5``).

        Resolution precedence per metric:
        1. ``context["metric_overrides"][metric_key]``
        2. ``context[metric_key]``
        3. ``perception.context[metric_key]``
        4. fallback default from selected policy/override

        Returns:
            A tuple ``(values, trace_metadata)`` where:
            - ``values`` maps each metric key to a float
            - ``trace_metadata`` documents policy, source and fallback diagnostics
        """
        metric_overrides_raw = context.get("metric_overrides")
        metric_overrides = (
            dict(metric_overrides_raw)
            if isinstance(metric_overrides_raw, Mapping)
            else {}
        )

        requested_policy = str(
            context.get("missing_metric_policy")
            or self.MISSING_METRIC_POLICY_DEFAULT_NEUTRAL
        )
        if (
            requested_policy
            not in self.SUPPORTED_MISSING_METRIC_POLICIES
        ):
            requested_policy = (
                self.MISSING_METRIC_POLICY_DEFAULT_NEUTRAL
            )

        default_for_missing = 0.0
        if (
            requested_policy
            == self.MISSING_METRIC_POLICY_DEFAULT_PESSIMISTIC
        ):
            default_for_missing = -1.0

        explicit_default_raw = context.get(
            "missing_metric_default"
        )
        if explicit_default_raw is not None:
            try:
                default_for_missing = float(explicit_default_raw)
            except (TypeError, ValueError):
                default_for_missing = (
                    0.0
                    if requested_policy
                    == self.MISSING_METRIC_POLICY_DEFAULT_NEUTRAL
                    else -1.0
                )

        strict_invalid = bool(
            context.get("missing_metric_strict_invalid", False)
        )

        fallback_dominance_threshold_raw = context.get(
            "fallback_dominance_threshold"
        )
        try:
            fallback_dominance_threshold = (
                float(fallback_dominance_threshold_raw)
                if fallback_dominance_threshold_raw is not None
                else 0.5
            )
        except (TypeError, ValueError):
            fallback_dominance_threshold = 0.5
        fallback_dominance_threshold = max(
            0.0, min(1.0, fallback_dominance_threshold)
        )

        resolved: dict[str, float] = {}
        missing_metrics: list[str] = []
        source_by_metric: dict[str, str] = {}
        fallback_applied_count = 0

        for metric_key in metric_keys:
            if metric_key in metric_overrides:
                raw = metric_overrides.get(metric_key)
                source_by_metric[metric_key] = (
                    "context.metric_overrides"
                )
            elif metric_key in context:
                raw = context.get(metric_key)
                source_by_metric[metric_key] = "context"
            elif metric_key in perception.context:
                raw = perception.context.get(metric_key)
                source_by_metric[metric_key] = (
                    "perception.context"
                )
            else:
                raw = default_for_missing
                missing_metrics.append(metric_key)
                source_by_metric[metric_key] = "default_missing"
                fallback_applied_count += 1

            if raw is None:
                if (
                    strict_invalid
                    and source_by_metric[metric_key]
                    != "default_missing"
                ):
                    raise ValueError(
                        f"Metric '{metric_key}' has invalid value None under strict mode"
                    )
                resolved[metric_key] = default_for_missing
                if metric_key not in missing_metrics:
                    missing_metrics.append(metric_key)
                source_by_metric[metric_key] = "default_invalid"
                fallback_applied_count += 1
                continue

            try:
                resolved[metric_key] = float(raw)
            except (TypeError, ValueError):
                if strict_invalid:
                    raise ValueError(
                        f"Metric '{metric_key}' has non-numeric value under strict mode"
                    )
                resolved[metric_key] = default_for_missing
                if metric_key not in missing_metrics:
                    missing_metrics.append(metric_key)
                source_by_metric[metric_key] = "default_invalid"
                fallback_applied_count += 1

        total_metrics = len(metric_keys)
        fallback_ratio = (
            float(fallback_applied_count) / float(total_metrics)
            if total_metrics > 0
            else 0.0
        )

        trace_metadata: JsonMap = {
            "missing_metric_policy": requested_policy,
            "missing_metric_default": float(default_for_missing),
            "missing_metric_strict_invalid": strict_invalid,
            "missing_metrics": sorted(missing_metrics),
            "fallback_applied_count": fallback_applied_count,
            "total_metrics": total_metrics,
            "fallback_ratio": fallback_ratio,
            "fallback_dominance_threshold": fallback_dominance_threshold,
            "fallback_dominates": fallback_ratio
            > fallback_dominance_threshold,
            "metric_sources": _canonical_json_map(
                source_by_metric
            ),
        }
        return resolved, trace_metadata

    def build_utility_frame(
        self,
        *,
        value: Union[float, list[float]],
        criteria_labels: Optional[list[str]] = None,
        metadata: Optional[JsonMap] = None,
    ) -> UtilityFrame:
        """Build a UtilityFrame with standardized, explicit metadata.

        Metadata added automatically (unless already present):
        - ``framework_id``
        - ``utility_shape``: ``"scalar"`` or ``"vector"``
        """
        resolved_metadata = dict(metadata or {})
        resolved_metadata.setdefault(
            "framework_id", self.framework_id
        )
        resolved_metadata.setdefault(
            "utility_shape",
            "vector" if isinstance(value, list) else "scalar",
        )
        return UtilityFrame(
            value=value,
            framework_id=self.framework_id,
            criteria_labels=list(criteria_labels or []),
            metadata=resolved_metadata,
        )
