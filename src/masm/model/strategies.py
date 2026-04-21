"""Strategy model primitives.

This module defines a minimal, serializable strategy tree.

A strategy is represented as:
- a root node;
- a set of nodes referencing existing action IDs;
- outcome branches from each node to the next node(s).

This module intentionally contains only declarative model objects. Projection,
execution, and utility ranking remain out of scope for this iteration.

TODO:
Support one-action-to-many-outcomes branching without changing the current
single-successor node model yet. The preferred future direction is Option A:
branch-specific projected outcomes should live on StrategyOutcomeBranch rather
than on StrategyNode, so each branch can carry its own successor perceived
state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Iterable, List, Mapping, Optional

from .base import (
    JsonMap,
    ModelObject,
    ObjectId,
    _canonical_json_map,
    _require_non_null_string,
)
from .actions import Action
from .perception import Perception
from .projection import (
    DefaultProjectionTool,
    ProjectedPerceptionState,
    ProjectionTool,
)
from .resources import Resource


def _canonical_json(value: Any) -> str:
    """Return deterministic JSON for sorting and validation."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Strategy metadata and conditions must be JSON-serializable"
        ) from exc


@dataclass
class StrategyBuildStep:
    """Recursive specification used by the minimal strategy builders."""

    action: Action
    children: list["StrategyBuildStep"] = field(default_factory=list)
    branch_label: str = "success"
    branch_probability: Optional[float] = None
    branch_condition: JsonMap = field(default_factory=dict)
    branch_metadata: JsonMap = field(default_factory=dict)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action.id:
            raise ValueError("StrategyBuildStep action id cannot be empty")
        if self.branch_probability is not None:
            if not 0.0 <= float(self.branch_probability) <= 1.0:
                raise ValueError(
                    "StrategyBuildStep branch_probability must be in [0, 1]"
                )
            self.branch_probability = float(self.branch_probability)


@dataclass
class StrategyOutcomeBranch:
    """Represents one projected outcome branch from a strategy node."""

    # TODO: Preferred future direction for multi-outcome projection (Option A):
    # move branch-specific projected successor state onto this branch model so
    # one action node can emit several alternative projected outcomes.

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

    # Current architecture: one node stores one projected successor state for
    # the action-perception pair it represents. Keep this model for now.
    # TODO: If one action later supports many projected outcomes, keep the node
    # as the action anchor and move alternative successor states to
    # StrategyOutcomeBranch rather than duplicating them here.

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


def _default_strategy_node_id(index: int, action: Action) -> ObjectId:
    return f"node-{index:04d}-{action.id}"


def _default_branching_strategy_node_id(
    path: tuple[int, ...], action: Action
) -> ObjectId:
    encoded_path = "-".join(f"{segment:04d}" for segment in path)
    return f"node-{encoded_path}-{action.id}"


def _project_strategy_action(
    action: Action,
    perception: Perception,
    projection_tool: ProjectionTool,
    resources: list[Resource],
    *,
    builder_name: str,
) -> tuple[ProjectedPerceptionState, JsonMap, str]:
    projection = projection_tool.project_action(
        action,
        perception,
        resources=resources,
    )
    projected_state = projection.projected_state
    if projected_state is None:
        raise ValueError(
            f"{builder_name} cannot continue without a projected successor perception"
        )
    return (
        projected_state,
        {"projection_basis": projection.metadata.get("projection_basis")},
        projection.status,
    )


def _build_branching_nodes_from_step(
    step: StrategyBuildStep,
    perception: Perception,
    path: tuple[int, ...],
    projection_tool: ProjectionTool,
    resources: list[Resource],
) -> tuple[StrategyNode, list[StrategyNode]]:
    node_id = _default_branching_strategy_node_id(path, step.action)
    projected_state, projection_metadata, projection_status = _project_strategy_action(
        step.action,
        perception,
        projection_tool,
        resources,
        builder_name="build_branching_strategy",
    )

    child_nodes: list[StrategyNode] = []
    outcome_branches: list[StrategyOutcomeBranch] = []
    for child_index, child_step in enumerate(step.children, start=1):
        child_node, descendant_nodes = _build_branching_nodes_from_step(
            child_step,
            projected_state.perception,
            path + (child_index,),
            projection_tool,
            resources,
        )
        child_nodes.extend(descendant_nodes)
        outcome_branches.append(
            StrategyOutcomeBranch(
                branch_id=f"{node_id}:branch-{child_index:04d}",
                label=child_step.branch_label,
                child_node_id=child_node.node_id,
                probability=child_step.branch_probability,
                condition=_canonical_json_map(child_step.branch_condition),
                metadata=_canonical_json_map(child_step.branch_metadata),
            )
        )

    node_metadata = dict(step.metadata)
    node_metadata.update(projection_metadata)
    node_metadata["projection_status"] = projection_status
    node = StrategyNode(
        node_id=node_id,
        action_id=step.action.id,
        source_perception_id=perception.id,
        projected_state=projected_state,
        outcome_branches=outcome_branches,
        metadata=node_metadata,
    )
    return node, [node, *child_nodes]


def build_branching_strategy(
    strategy_id: ObjectId,
    initial_perception: Perception,
    root_step: StrategyBuildStep,
    *,
    resources: Iterable[Resource] = (),
    projection_tool: Optional[ProjectionTool] = None,
    projection_policy: str = "perception_first",
) -> Strategy:
    """Build a minimal strategy tree from a recursive step specification."""
    resolved_projection_tool = projection_tool or DefaultProjectionTool()
    resource_list = list(resources)
    root_node, nodes = _build_branching_nodes_from_step(
        root_step,
        initial_perception,
        (1,),
        resolved_projection_tool,
        resource_list,
    )
    strategy = Strategy(
        id=strategy_id,
        actor_id=initial_perception.actor_id,
        root_node_id=root_node.node_id,
        nodes=nodes,
        projection_policy=projection_policy,
    )
    strategy.validate_tree()
    return strategy


def build_linear_strategy(
    strategy_id: ObjectId,
    initial_perception: Perception,
    actions: Iterable[Action],
    *,
    resources: Iterable[Resource] = (),
    projection_tool: Optional[ProjectionTool] = None,
    projection_policy: str = "perception_first",
) -> Strategy:
    """Build a minimal chained strategy from an ordered action sequence.

    Each action is projected against the current perceived state, and the next
    node consumes the successor projected perception produced by the previous
    node. The builder currently constructs a linear success chain only.
    """
    ordered_actions = list(actions)
    if not ordered_actions:
        raise ValueError("build_linear_strategy requires at least one action")

    resolved_projection_tool = projection_tool or DefaultProjectionTool()
    resource_list = list(resources)
    current_perception = initial_perception
    nodes: list[StrategyNode] = []
    planned_node_ids = [
        _default_strategy_node_id(index, action)
        for index, action in enumerate(ordered_actions, start=1)
    ]

    for index, action in enumerate(ordered_actions):
        projected_state, projection_metadata, projection_status = (
            _project_strategy_action(
                action,
                current_perception,
                resolved_projection_tool,
                resource_list,
                builder_name="build_linear_strategy",
            )
        )

        next_node_id = (
            planned_node_ids[index + 1] if index + 1 < len(planned_node_ids) else None
        )
        outcome_branches = []
        if next_node_id is not None:
            outcome_branches.append(
                StrategyOutcomeBranch(
                    branch_id=f"{planned_node_ids[index]}:success",
                    label="success",
                    child_node_id=next_node_id,
                    metadata={"projection_status": projection_status},
                )
            )

        node_metadata = dict(projection_metadata)
        node_metadata["projection_status"] = projection_status
        nodes.append(
            StrategyNode(
                node_id=planned_node_ids[index],
                action_id=action.id,
                source_perception_id=current_perception.id,
                projected_state=projected_state,
                outcome_branches=outcome_branches,
                metadata=node_metadata,
            )
        )
        current_perception = projected_state.perception

    strategy = Strategy(
        id=strategy_id,
        actor_id=initial_perception.actor_id,
        root_node_id=planned_node_ids[0],
        nodes=nodes,
        projection_policy=projection_policy,
    )
    strategy.validate_tree()
    return strategy
