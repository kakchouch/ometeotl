"""Goal model primitives.

This module defines goals as first-class model objects enabling domain-specific
teleology while preserving the framework's teleological neutrality (A-23, P-1).

A goal is represented as:
- a root-level goal with a target_condition (domain-specific predicate);
- optional intermediate subgoals (A-13) arranged in a goal hierarchy;
- linkage to an actor and zero or more strategies pursuing the goal.

This module is intentionally declarative. Execution, utility ranking, and
goal-satisfaction remain out of scope for this iteration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional

from .base import (
    JsonMap,
    ModelObject,
    ObjectId,
    _canonical_json_map,
    _require_non_null_string,
)


@dataclass
class GoalBuildStep:
    """Recursive specification used by the goal hierarchy builder.

    Mirrors StrategyBuildStep but for goals: wraps goal specification + children.
    """

    kind: str  # "final" or "intermediate"
    actor_id: ObjectId
    target_condition: JsonMap
    horizon: JsonMap = field(default_factory=dict)
    priority: float = 1.0
    status: str = "active"
    children: list["GoalBuildStep"] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("GoalBuildStep actor_id cannot be empty")
        if self.kind not in ("final", "intermediate"):
            raise ValueError("GoalBuildStep kind must be 'final' or 'intermediate'")
        if not 0.0 <= float(self.priority) <= 1.0:
            raise ValueError("GoalBuildStep priority must be in [0, 1]")
        self.priority = float(self.priority)


@dataclass
class Goal(ModelObject):
    """A goal represents an objective an actor may pursue.

    Goals are domain-specific and domain-defined. This class is intentionally
    open-ended with respect to target_condition, enabling any domain to define
    what constitutes goal achievement without imposing a concrete teleology
    on the framework (A-23, P-1).

    Core specs addressed: A-4 (actor), A-12 (objectives), A-13 (final/intermediate),
    A-14 (capacity), A-24 (emerging irrationality).
    """

    object_type: str = "goal"
    actor_id: ObjectId = ""
    kind: str = "final"  # "final" or "intermediate"
    priority: float = 1.0
    status: str = "active"  # "active", "achieved", "abandoned", "blocked"
    horizon: JsonMap = field(default_factory=dict)
    target_condition: JsonMap = field(default_factory=dict)
    target_perception_id: Optional[ObjectId] = None
    parent_goal_id: Optional[ObjectId] = None
    child_goal_ids: List[ObjectId] = field(default_factory=list)
    strategy_ids: List[ObjectId] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.object_type != "goal":
            self.object_type = "goal"
        if not self.id:
            raise ValueError("Goal id cannot be empty")
        if not self.actor_id:
            raise ValueError("Goal actor_id cannot be empty")
        if self.kind not in ("final", "intermediate"):
            raise ValueError("Goal kind must be 'final' or 'intermediate'")
        if not 0.0 <= float(self.priority) <= 1.0:
            raise ValueError("Goal priority must be in [0, 1]")
        self.priority = float(self.priority)
        if self.status not in ("active", "achieved", "abandoned", "blocked"):
            raise ValueError(
                "Goal status must be one of: active, achieved, abandoned, blocked"
            )

    def add_child_goal(self, goal_id: ObjectId) -> None:
        """Register a child goal, maintaining sorted unique list."""
        if not goal_id:
            raise ValueError("goal_id cannot be empty")
        if goal_id not in self.child_goal_ids:
            self.child_goal_ids = sorted(list(set(self.child_goal_ids) | {goal_id}))

    def remove_child_goal(self, goal_id: ObjectId) -> None:
        """Remove a child goal from the list."""
        self.child_goal_ids = [gid for gid in self.child_goal_ids if gid != goal_id]

    def add_strategy(self, strategy_id: ObjectId) -> None:
        """Register a strategy aimed at this goal, maintaining sorted unique list."""
        if not strategy_id:
            raise ValueError("strategy_id cannot be empty")
        if strategy_id not in self.strategy_ids:
            self.strategy_ids = sorted(list(set(self.strategy_ids) | {strategy_id}))

    def remove_strategy(self, strategy_id: ObjectId) -> None:
        """Remove a strategy from the list."""
        self.strategy_ids = [sid for sid in self.strategy_ids if sid != strategy_id]

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the goal."""
        base = super().to_dict()
        base.update(
            {
                "actor_id": self.actor_id,
                "kind": self.kind,
                "priority": float(self.priority),
                "status": self.status,
                "horizon": _canonical_json_map(self.horizon),
                "target_condition": _canonical_json_map(self.target_condition),
                "target_perception_id": self.target_perception_id,
                "parent_goal_id": self.parent_goal_id,
                "child_goal_ids": sorted(self.child_goal_ids),
                "strategy_ids": sorted(self.strategy_ids),
            }
        )
        return base

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Goal":
        """Reconstruct a goal from its canonical representation."""
        base_obj = ModelObject.from_dict(data)
        return cls(
            **base_obj._base_kwargs(),
            actor_id=_require_non_null_string(data, "actor_id"),
            kind=str(data.get("kind") or "final"),
            priority=float(data.get("priority") or 1.0),
            status=str(data.get("status") or "active"),
            horizon=dict(data.get("horizon") or {}),
            target_condition=dict(data.get("target_condition") or {}),
            target_perception_id=(
                str(data["target_perception_id"])
                if data.get("target_perception_id")
                else None
            ),
            parent_goal_id=(
                str(data["parent_goal_id"]) if data.get("parent_goal_id") else None
            ),
            child_goal_ids=[str(gid) for gid in (data.get("child_goal_ids") or [])],
            strategy_ids=[str(sid) for sid in (data.get("strategy_ids") or [])],
        )


@dataclass
class GoalDecompositionTree:
    """Container for a goal hierarchy with validation and lookup.

    Analogous to how Strategy contains StrategyNode, GoalDecompositionTree
    contains Goal objects linked by parent-child relations.
    """

    root_goal_id: ObjectId
    goals: dict[ObjectId, Goal] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.root_goal_id:
            raise ValueError("GoalDecompositionTree root_goal_id cannot be empty")
        if self.root_goal_id not in self.goals:
            raise ValueError(
                f"GoalDecompositionTree root_goal_id '{self.root_goal_id}' "
                "must reference a registered goal"
            )
        root_goal = self.goals[self.root_goal_id]
        if root_goal.parent_goal_id is not None:
            raise ValueError(
                f"GoalDecompositionTree root goal '{self.root_goal_id}' "
                "must not have a parent_goal_id"
            )

    def add_goal(self, goal: Goal) -> None:
        """Register a goal in the tree, raising on duplicate ID."""
        if goal.id in self.goals:
            raise ValueError(f"Duplicate goal id: {goal.id}")
        self.goals[goal.id] = goal

    def get_goal(self, goal_id: ObjectId) -> Optional[Goal]:
        """Return a goal by ID, if present."""
        return self.goals.get(goal_id)

    def children_of(self, goal_id: ObjectId) -> list[Goal]:
        """Return all direct child goals of a given goal."""
        parent_goal = self.get_goal(goal_id)
        if parent_goal is None:
            return []
        return [
            self.goals[child_id]
            for child_id in parent_goal.child_goal_ids
            if child_id in self.goals
        ]

    def parent_of(self, goal_id: ObjectId) -> Optional[Goal]:
        """Return the parent goal if it exists."""
        goal = self.get_goal(goal_id)
        if goal is None or goal.parent_goal_id is None:
            return None
        return self.goals.get(goal.parent_goal_id)

    def validate_tree(self) -> None:
        """Validate structural integrity: no cycles, all refs valid, root has no parent."""
        # Validate root has no parent
        root_goal = self.goals.get(self.root_goal_id)
        if root_goal is None:
            raise ValueError(
                f"GoalDecompositionTree root_goal_id '{self.root_goal_id}' "
                "must reference a registered goal"
            )
        if root_goal.parent_goal_id is not None:
            raise ValueError(
                "GoalDecompositionTree root goal must not have a parent_goal_id"
            )

        # Validate all child references resolve to existing goals
        for goal_id, goal in self.goals.items():
            for child_id in goal.child_goal_ids:
                if child_id not in self.goals:
                    raise ValueError(
                        f"Goal '{goal_id}' references unknown child goal '{child_id}'"
                    )
            if goal.parent_goal_id is not None:
                if goal.parent_goal_id not in self.goals:
                    raise ValueError(
                        f"Goal '{goal_id}' references unknown parent goal "
                        f"'{goal.parent_goal_id}'"
                    )

        # Validate no cycles using DFS
        visited: set[ObjectId] = set()
        rec_stack: set[ObjectId] = set()

        def has_cycle_from(goal_id: ObjectId) -> bool:
            visited.add(goal_id)
            rec_stack.add(goal_id)
            goal = self.goals[goal_id]
            for child_id in goal.child_goal_ids:
                if child_id not in visited:
                    if has_cycle_from(child_id):
                        return True
                elif child_id in rec_stack:
                    return True
            rec_stack.remove(goal_id)
            return False

        if has_cycle_from(self.root_goal_id):
            raise ValueError("GoalDecompositionTree contains a cycle")

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the tree."""
        return {
            "root_goal_id": self.root_goal_id,
            "goals": {
                goal_id: goal.to_dict() for goal_id, goal in sorted(self.goals.items())
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GoalDecompositionTree":
        """Reconstruct a goal decomposition tree from mapping data."""
        root_goal_id = _require_non_null_string(data, "root_goal_id")
        goals_data = data.get("goals") or {}
        goals = {
            goal_id: Goal.from_dict(goal_data)
            for goal_id, goal_data in goals_data.items()
        }
        tree = cls(root_goal_id=root_goal_id, goals=goals)
        tree.validate_tree()
        return tree


def _default_goal_id(index: int, actor_id: ObjectId, kind: str) -> ObjectId:
    """Generate a deterministic goal ID."""
    return f"goal-{index:04d}-{actor_id}-{kind}"


def _default_hierarchy_goal_id(
    path: tuple[int, ...], actor_id: ObjectId, kind: str
) -> ObjectId:
    """Generate a deterministic goal ID for hierarchical goals."""
    encoded_path = "-".join(f"{segment:04d}" for segment in path)
    return f"goal-{encoded_path}-{actor_id}-{kind}"


def build_goal_hierarchy(
    root_step: GoalBuildStep,
) -> GoalDecompositionTree:
    """Build a goal decomposition tree from a recursive step specification.

    Mirrors build_branching_strategy but for goals. Creates Goal objects from
    the tree of GoalBuildStep nodes and assembles them into a
    GoalDecompositionTree with validated parent-child links.

    Args:
        root_step: Root GoalBuildStep specification (including children for
                   intermediate subgoals).

    Returns:
        A validated GoalDecompositionTree.

    Raises:
        ValueError: If the goal hierarchy cannot be constructed or validated.
    """

    def _build_goals_from_step(
        step: GoalBuildStep,
        path: tuple[int, ...],
        parent_goal_id: Optional[ObjectId] = None,
    ) -> tuple[Goal, list[Goal]]:
        """Recursively build goals from a step specification.

        Returns: (root_goal_from_step, all_goals_including_descendants)
        """
        goal_id = _default_hierarchy_goal_id(path, step.actor_id, step.kind)
        goal = Goal(
            id=goal_id,
            actor_id=step.actor_id,
            kind=step.kind,
            priority=step.priority,
            status=step.status,
            horizon=dict(step.horizon),
            target_condition=dict(step.target_condition),
            parent_goal_id=parent_goal_id,
            child_goal_ids=[],
            strategy_ids=[],
            attributes=_canonical_json_map(step.metadata),
        )

        all_goals: list[Goal] = [goal]
        child_goal_ids: list[ObjectId] = []

        for child_index, child_step in enumerate(step.children, start=1):
            child_goal, descendant_goals = _build_goals_from_step(
                child_step,
                path + (child_index,),
                parent_goal_id=goal_id,
            )
            all_goals.extend(descendant_goals)
            child_goal_ids.append(child_goal.id)

        if child_goal_ids:
            goal.child_goal_ids = sorted(child_goal_ids)

        return goal, all_goals

    root_goal, all_goals = _build_goals_from_step(root_step, (1,), parent_goal_id=None)

    # Assemble the tree
    goals_dict = {goal.id: goal for goal in all_goals}
    tree = GoalDecompositionTree(root_goal_id=root_goal.id, goals=goals_dict)
    tree.validate_tree()
    return tree
