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
from typing import Any, Mapping, Union

from .base import JsonMap, ObjectId
from .actors import Actor
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
        if not self.framework_id:
            raise ValueError("UtilityFrame framework_id cannot be empty")
        if isinstance(self.value, list):
            if self.criteria_labels and len(self.criteria_labels) != len(self.value):
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
                self.value if not isinstance(self.value, list) else list(self.value)
            ),
            "framework_id": self.framework_id,
            "criteria_labels": list(self.criteria_labels),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "UtilityFrame":
        """Reconstruct a utility frame from mapping data."""
        raw_value = data.get("value")
        if isinstance(raw_value, list):
            value: Union[float, list[float]] = [float(v) for v in raw_value]
        else:
            value = float(raw_value) if raw_value is not None else 0.0

        return cls(
            value=value,
            framework_id=str(data.get("framework_id") or ""),
            criteria_labels=[
                str(label) for label in (data.get("criteria_labels") or [])
            ],
            metadata=dict(data.get("metadata") or {}),
        )


class UtilityFunction(ABC):
    """Abstract base class for utility functions.

    A utility function evaluates the utility of a perceived state for an actor
    relative to an interpretive framework (A-22). Utility is domain-specific and
    framework-dependent; this interface imposes no concrete objectives (P-1, A-23).

    Core specs addressed: A-22 (interpretive framework), G-6 (multi-criteria utility).

    Subclasses must implement:
    - `evaluate(perception, actor, context)` — return a UtilityFrame
    - `is_multi_criteria` property — True for vector-valued utilities

    Example:
        class MaxResourceUtility(UtilityFunction):
            def __init__(self, framework_id: str):
                self.framework_id = framework_id

            @property
            def is_multi_criteria(self) -> bool:
                return False

            def evaluate(
                self,
                perception: Perception,
                actor: Actor,
                context: JsonMap,
            ) -> UtilityFrame:
                # Count resources in perceived state
                resource_count = len(perception.perceived_spaces)
                return UtilityFrame(
                    value=float(resource_count),
                    framework_id=self.framework_id,
                )
    """

    @property
    @abstractmethod
    def framework_id(self) -> str:
        """Identifier of the interpretive framework this utility function uses.

        The framework_id ties the utility evaluation to a domain-specific
        context (A-22) without imposing it on the core architecture.
        """
        pass

    @property
    @abstractmethod
    def is_multi_criteria(self) -> bool:
        """Return True if this function produces vector-valued utilities (G-6)."""
        pass

    @abstractmethod
    def evaluate(
        self,
        perception: Perception,
        actor: Actor,
        context: JsonMap,
    ) -> UtilityFrame:
        """Evaluate utility of a perceived state for an actor.

        Args:
            perception: The actor's current or projected perception.
            actor: The actor evaluating utility.
            context: Domain-specific context (e.g., constraints, preferences).

        Returns:
            A UtilityFrame containing the scalar or vector utility value(s),
            framework reference, and optional metadata.

        Raises:
            ValueError: If perception, actor, or context are invalid.
        """
        pass
