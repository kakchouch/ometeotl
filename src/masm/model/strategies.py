"""Strategy model primitives.

This module defines a minimal, serializable strategy tree.

A strategy is represented as:
- a root node;
- a set of nodes referencing existing action IDs;
- outcome branches from each node to the next node(s).

This module intentionally contains only declarative model objects. Projection,
execution, and utility ranking remain out of scope for this iteration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, List, Mapping, Optional

from .base import (
    JsonMap,
    ModelObject,
    ObjectId,
    _canonical_json_map,
    _require_non_null_string,
)
from .projection import ProjectedPerceptionState


def _canonical_json(value: Any) -> str:
    """Return deterministic JSON for sorting and validation."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Strategy metadata and conditions must be JSON-serializable"
        ) from exc


@dataclass
class StrategyOutcomeBranch:
    """Represents one projected outcome branch from a strategy node."""

    branch_id: str
    label: str = "success"
    child_node_id: Optional[ObjectId] = None
    probability: Optional[float] = None
    condition: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.branch_id:
            raise ValueError("StrategyOutcomeBranch branch_id cannot be empty")
        if self.probability is not None:
            if not 0.0 <= float(self.probability) <= 1.0:
                raise ValueError("StrategyOutcomeBranch probability must be in [0, 1]")
            self.probability = float(self.probability)

    def to_dict(self) -> JsonMap:
        """Serialize the branch in canonical form."""
        return {
            "branch_id": self.branch_id,
            "label": self.label,
            "child_node_id": self.child_node_id,
            "probability": self.probability,
            "condition": _canonical_json_map(self.condition),
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StrategyOutcomeBranch":
        """Deserialize a branch from mapping data."""
        probability_raw = data.get("probability")
        return cls(
            branch_id=_require_non_null_string(data, "branch_id"),
            label=str(data.get("label") or "success"),
            child_node_id=(
                str(data["child_node_id"]) if data.get("child_node_id") else None
            ),
            probability=(
                float(probability_raw) if probability_raw is not None else None
            ),
            condition=dict(data.get("condition") or {}),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class StrategyNode:
    """A strategy node binding one action to one or more projected outcomes."""

    node_id: ObjectId
    action_id: ObjectId
    source_perception_id: Optional[ObjectId] = None
    projected_state: Optional[ProjectedPerceptionState] = None
    outcome_branches: List[StrategyOutcomeBranch] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("StrategyNode node_id cannot be empty")
        if not self.action_id:
            raise ValueError("StrategyNode action_id cannot be empty")
        if self.source_perception_id is not None and not self.source_perception_id:
            raise ValueError("StrategyNode source_perception_id cannot be empty")
        if self.projected_state is not None:
            if self.projected_state.generating_action_id != self.action_id:
                raise ValueError(
                    "StrategyNode projected_state must match the node action_id"
                )
            if self.source_perception_id is None:
                self.source_perception_id = self.projected_state.source_perception_id
            elif self.source_perception_id != self.projected_state.source_perception_id:
                raise ValueError(
                    "StrategyNode source_perception_id must match the projected_state source"
                )

    @property
    def successor_perception_id(self) -> Optional[ObjectId]:
        """Return the successor perception ID produced by this node, if any."""
        if self.projected_state is None:
            return None
        return self.projected_state.perception.id

    def to_dict(self) -> JsonMap:
        """Serialize the node in canonical form."""
        return {
            "node_id": self.node_id,
            "action_id": self.action_id,
            "source_perception_id": self.source_perception_id,
            "projected_state": (
                self.projected_state.to_dict()
                if self.projected_state is not None
                else None
            ),
            "outcome_branches": [
                branch.to_dict()
                for branch in sorted(
                    self.outcome_branches,
                    key=lambda branch: (
                        branch.branch_id,
                        branch.label,
                        str(branch.child_node_id),
                        str(branch.probability),
                        _canonical_json(branch.condition),
                        _canonical_json(branch.metadata),
                    ),
                )
            ],
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StrategyNode":
        """Deserialize a strategy node from mapping data."""
        return cls(
            node_id=_require_non_null_string(data, "node_id"),
            action_id=_require_non_null_string(data, "action_id"),
            source_perception_id=(
                str(data["source_perception_id"])
                if data.get("source_perception_id")
                else None
            ),
            projected_state=(
                ProjectedPerceptionState.from_dict(data["projected_state"])
                if data.get("projected_state") is not None
                else None
            ),
            outcome_branches=[
                StrategyOutcomeBranch.from_dict(raw_branch)
                for raw_branch in (data.get("outcome_branches") or [])
            ],
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class Strategy(ModelObject):
    """Declarative strategy tree referencing action IDs and outcome branches."""

    object_type: str = "strategy"
    actor_id: ObjectId = ""
    root_node_id: ObjectId = ""
    nodes: List[StrategyNode] = field(default_factory=list)
    projection_policy: str = "perception_first"

    def __post_init__(self) -> None:
        if self.object_type != "strategy":
            self.object_type = "strategy"
        if not self.id:
            raise ValueError("Strategy id cannot be empty")
        if not self.actor_id:
            raise ValueError("Strategy actor_id cannot be empty")
        if not self.root_node_id:
            raise ValueError("Strategy root_node_id cannot be empty")
        if not self.projection_policy:
            raise ValueError("Strategy projection_policy cannot be empty")

    def add_node(self, node: StrategyNode) -> None:
        """Add a node while preserving unique node IDs."""
        if any(existing.node_id == node.node_id for existing in self.nodes):
            raise ValueError(f"Duplicate strategy node id: {node.node_id}")
        self.nodes.append(node)

    def get_node(self, node_id: ObjectId) -> Optional[StrategyNode]:
        """Return a strategy node by ID, if present."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def validate_tree(self) -> None:
        """Validate minimal structural integrity of the strategy tree."""
        node_ids = {node.node_id for node in self.nodes}
        node_index = {node.node_id: node for node in self.nodes}
        if self.root_node_id not in node_ids:
            raise ValueError("Strategy root_node_id must reference an existing node")

        for node in self.nodes:
            seen_branches: set[str] = set()
            for branch in node.outcome_branches:
                if branch.branch_id in seen_branches:
                    raise ValueError(
                        f"Duplicate branch id '{branch.branch_id}' in node '{node.node_id}'"
                    )
                seen_branches.add(branch.branch_id)
                if branch.child_node_id and branch.child_node_id not in node_ids:
                    raise ValueError(
                        "Strategy branch child_node_id must reference an existing node"
                    )
                if branch.child_node_id is None:
                    continue

                child_node = node_index[branch.child_node_id]
                if node.projected_state is None:
                    continue

                expected_source_perception_id = node.successor_perception_id
                if expected_source_perception_id is None:
                    continue
                if child_node.source_perception_id is None:
                    raise ValueError(
                        "Strategy child node must declare the parent projected perception"
                    )
                if child_node.source_perception_id != expected_source_perception_id:
                    raise ValueError(
                        "Strategy child node must consume the parent projected perception"
                    )

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the strategy."""
        base = super().to_dict()
        base.update(
            {
                "actor_id": self.actor_id,
                "root_node_id": self.root_node_id,
                "nodes": [
                    node.to_dict()
                    for node in sorted(self.nodes, key=lambda node: node.node_id)
                ],
                "projection_policy": self.projection_policy,
            }
        )
        return base

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Strategy":
        """Reconstruct a strategy from its canonical representation."""
        base_obj = ModelObject.from_dict(data)
        return cls(
            **base_obj._base_kwargs(),
            actor_id=_require_non_null_string(data, "actor_id"),
            root_node_id=_require_non_null_string(data, "root_node_id"),
            nodes=[
                StrategyNode.from_dict(raw_node)
                for raw_node in (data.get("nodes") or [])
            ],
            projection_policy=str(data.get("projection_policy") or "perception_first"),
        )
