"""
This module defines Sensor, CoverageRule, and NoiseRule.

A Sensor is the interface between a World and an actor's Perception.
It iterates over the world's registered sub-spaces, object memberships,
and space relations. For each element it:

  1. Applies all CoverageRules in AND-logic — if any rule returns False,
     the element is omitted from the perception (incompleteness).
  2. Creates a deep copy of the element so the original world is never
     mutated.
  3. Applies all NoiseRules in sequence to that copy — each rule may
     distort the value and emit metadata describing the distortion.
  4. Wraps the result in the corresponding Perceived* container with the
     configured default epistemic status.

Domain-specific behaviour is introduced by subclassing CoverageRule
and/or NoiseRule; multiple rules may be composed on a single Sensor.

Core specs addressed: A-9, A-10, A-11, F-5, F-14.
"""

from __future__ import annotations

import copy
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from .perception import (
    VALID_EPISTEMIC_STATUSES,
    Perception,
    PerceivedMembership,
    PerceivedRelation,
    PerceivedSpace,
)
from .spaces import Space, SpaceObjectMembership
from .space_relations import SpaceRelation
from .world import World

JsonMap = Dict[str, Any]
ObjectId = str


# ---------------------------------------------------------------------------
# Coverage rules
# ---------------------------------------------------------------------------


class CoverageRule(ABC):
    """Abstract base for domain-specific coverage rules.

    A coverage rule answers yes/no for each world element: should this
    element appear in the perception of the given actor?

    All rules in a Sensor's ``coverage_rules`` list are evaluated; an
    element is included only if *all* rules return True (logical AND).
    Override one or more methods to implement selective coverage.
    """

    @abstractmethod
    def covers_space(self, space: Space, actor_id: ObjectId, world: World) -> bool:
        """Return True if the space should appear in the actor's perception."""
        ...

    @abstractmethod
    def covers_membership(
        self,
        membership: SpaceObjectMembership,
        actor_id: ObjectId,
        world: World,
    ) -> bool:
        """Return True if the membership should appear in the actor's perception."""
        ...

    @abstractmethod
    def covers_relation(
        self, relation: SpaceRelation, actor_id: ObjectId, world: World
    ) -> bool:
        """Return True if the space relation should appear in the actor's perception."""
        ...


class TotalCoverageRule(CoverageRule):
    """Default rule: every world element is visible to every actor.

    This is the transparent / omniscient sensor baseline.
    """

    def covers_space(self, space: Space, actor_id: ObjectId, world: World) -> bool:
        return True

    def covers_membership(
        self,
        membership: SpaceObjectMembership,
        actor_id: ObjectId,
        world: World,
    ) -> bool:
        return True

    def covers_relation(
        self, relation: SpaceRelation, actor_id: ObjectId, world: World
    ) -> bool:
        return True


# ---------------------------------------------------------------------------
# Noise rules
# ---------------------------------------------------------------------------


class NoiseRule(ABC):
    """Abstract base for domain-specific noise rules.

    A noise rule may distort the content of a perceived element. It
    receives a *copy* of the element (the original world data is never
    touched) and must return a (possibly modified) copy together with a
    metadata dict documenting the specific distortions applied.

    Multiple noise rules may be chained on a Sensor; they are applied in
    order, each rule operating on the output of the previous one.
    """

    @abstractmethod
    def apply_to_space(self, space: Space, actor_id: ObjectId) -> Tuple[Space, JsonMap]:
        """Return a (potentially distorted) space copy and noise metadata."""
        ...

    @abstractmethod
    def apply_to_membership(
        self, membership: SpaceObjectMembership, actor_id: ObjectId
    ) -> Tuple[SpaceObjectMembership, JsonMap]:
        """Return a (potentially distorted) membership copy and noise metadata."""
        ...

    @abstractmethod
    def apply_to_relation(
        self, relation: SpaceRelation, actor_id: ObjectId
    ) -> Tuple[SpaceRelation, JsonMap]:
        """Return a (potentially distorted) relation copy and noise metadata."""
        ...


class IdentityNoiseRule(NoiseRule):
    """Default rule: no noise is applied; all values are passed through unchanged."""

    def apply_to_space(self, space: Space, actor_id: ObjectId) -> Tuple[Space, JsonMap]:
        return space, {}

    def apply_to_membership(
        self, membership: SpaceObjectMembership, actor_id: ObjectId
    ) -> Tuple[SpaceObjectMembership, JsonMap]:
        return membership, {}

    def apply_to_relation(
        self, relation: SpaceRelation, actor_id: ObjectId
    ) -> Tuple[SpaceRelation, JsonMap]:
        return relation, {}


# ---------------------------------------------------------------------------
# Sensor
# ---------------------------------------------------------------------------


@dataclass
class Sensor:
    """Interface between a World and an actor's Perception.

    Parameters
    ----------
    coverage_rules:
        Ordered list of CoverageRule instances evaluated in AND-logic.
        Defaults to ``[TotalCoverageRule()]``.
    noise_rules:
        Ordered list of NoiseRule instances applied in sequence to each
        perceived element copy.  Defaults to ``[IdentityNoiseRule()]``.
    default_epistemic_status:
        Epistemic label assigned to every perceived element produced by
        this sensor.  Must be one of ``VALID_EPISTEMIC_STATUSES``.
        Defaults to ``"certain"``.
    """

    coverage_rules: List[CoverageRule] = field(
        default_factory=lambda: [TotalCoverageRule()]
    )
    noise_rules: List[NoiseRule] = field(default_factory=lambda: [IdentityNoiseRule()])
    default_epistemic_status: str = "certain"

    def __post_init__(self) -> None:
        if self.default_epistemic_status not in VALID_EPISTEMIC_STATUSES:
            raise ValueError(
                f"Invalid default_epistemic_status: '{self.default_epistemic_status}'. "
                f"Must be one of {sorted(VALID_EPISTEMIC_STATUSES)}."
            )

    # --- Public API ---------------------------------------------------------

    def sense(
        self,
        world: World,
        actor_id: ObjectId,
        timestamp: Optional[Union[int, float, str]] = None,
    ) -> Perception:
        """Build a Perception of the given world for the given actor.

        The returned Perception is fully insulated: subsequent changes to
        the world do not affect it, and noise applied during sensing does
        not mutate the original world objects.

        Parameters
        ----------
        timestamp:
            Optional simulation timestamp for this snapshot. Must be an
            ``int``, ``float``, or ``str`` to guarantee a deterministic
            string representation. When provided it is embedded in the
            perception ID, making the ID deterministic for the
            (actor_id, world.id, timestamp) triplet. When omitted a
            random UUID suffix ensures uniqueness across calls.
        """
        if timestamp is not None:
            if not isinstance(timestamp, (int, float, str)):
                raise TypeError(
                    f"timestamp must be int, float, or str, got {type(timestamp).__name__}"
                )
            perception_id = f"perception-{actor_id}-{world.id}-{timestamp!s}"
        else:
            perception_id = f"perception-{actor_id}-{world.id}-{uuid.uuid4().hex}"
        perception = Perception(
            id=perception_id,
            actor_id=actor_id,
            source_id=world.id,
            timestamp=timestamp,
        )
        self._sense_spaces(world, actor_id, perception)
        self._sense_memberships(world, actor_id, perception)
        self._sense_relations(world, actor_id, perception)
        return perception

    # --- Internal helpers ---------------------------------------------------

    def _sense_spaces(
        self, world: World, actor_id: ObjectId, perception: Perception
    ) -> None:
        for space_id, space in world.space_object_graph.spaces.items():
            if not self._covers_space(space, actor_id, world):
                continue
            # Deep copy before noise so the world is never mutated.
            space_copy = copy.deepcopy(space)
            space_copy, noise_meta = self._apply_noise_to_space(space_copy, actor_id)
            perception.perceived_spaces[space_id] = PerceivedSpace(
                space=space_copy,
                epistemic_status=self.default_epistemic_status,
                noise_metadata=noise_meta,
            )

    def _sense_memberships(
        self, world: World, actor_id: ObjectId, perception: Perception
    ) -> None:
        for membership in world.space_object_graph.object_memberships:
            if not self._covers_membership(membership, actor_id, world):
                continue
            membership_copy = copy.deepcopy(membership)
            membership_copy, noise_meta = self._apply_noise_to_membership(
                membership_copy, actor_id
            )
            perception.perceived_memberships.append(
                PerceivedMembership(
                    membership=membership_copy,
                    epistemic_status=self.default_epistemic_status,
                    noise_metadata=noise_meta,
                )
            )

    def _sense_relations(
        self, world: World, actor_id: ObjectId, perception: Perception
    ) -> None:
        for relation in world.space_relation_graph.relations:
            if not self._covers_relation(relation, actor_id, world):
                continue
            relation_copy = copy.deepcopy(relation)
            relation_copy, noise_meta = self._apply_noise_to_relation(
                relation_copy, actor_id
            )
            perception.perceived_relations.append(
                PerceivedRelation(
                    relation=relation_copy,
                    epistemic_status=self.default_epistemic_status,
                    noise_metadata=noise_meta,
                )
            )

    # --- Rule aggregators ---------------------------------------------------

    def _covers_space(self, space: Space, actor_id: ObjectId, world: World) -> bool:
        return all(r.covers_space(space, actor_id, world) for r in self.coverage_rules)

    def _covers_membership(
        self, membership: SpaceObjectMembership, actor_id: ObjectId, world: World
    ) -> bool:
        return all(
            r.covers_membership(membership, actor_id, world)
            for r in self.coverage_rules
        )

    def _covers_relation(
        self, relation: SpaceRelation, actor_id: ObjectId, world: World
    ) -> bool:
        return all(
            r.covers_relation(relation, actor_id, world) for r in self.coverage_rules
        )

    def _apply_noise_to_space(
        self, space: Space, actor_id: ObjectId
    ) -> Tuple[Space, JsonMap]:
        merged_meta: JsonMap = {}
        for rule in self.noise_rules:
            space, meta = rule.apply_to_space(space, actor_id)
            merged_meta.update(meta)
        return space, merged_meta

    def _apply_noise_to_membership(
        self, membership: SpaceObjectMembership, actor_id: ObjectId
    ) -> Tuple[SpaceObjectMembership, JsonMap]:
        merged_meta: JsonMap = {}
        for rule in self.noise_rules:
            membership, meta = rule.apply_to_membership(membership, actor_id)
            merged_meta.update(meta)
        return membership, merged_meta

    def _apply_noise_to_relation(
        self, relation: SpaceRelation, actor_id: ObjectId
    ) -> Tuple[SpaceRelation, JsonMap]:
        merged_meta: JsonMap = {}
        for rule in self.noise_rules:
            relation, meta = rule.apply_to_relation(relation, actor_id)
            merged_meta.update(meta)
        return relation, merged_meta
