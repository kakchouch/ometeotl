"""AdjacencyNetworkSpace: ready-to-use foundations-layer network class.

Analogous to GeometricSpace in the spatial layer but mutable, since
network topologies evolve over time.

The central design guarantee:
  ``_relations: SpaceRelationGraph`` IS the topology — the single canonical
  source of truth.  ``add_connection()`` delegates to
  ``SpaceRelationGraph.add_relation()``, which enforces all algebraic
  constraints defined in ometeotl_core:
    - symmetric relations (adjacent_to, intersects_with) are canonicalized
    - antisymmetric relations (contains_space) prevent inverses
    - self-loops are rejected for non-reflexive types
    - duplicate relations are silently ignored

There is no separate AdjacencyGraph that could drift out of sync.

Usage:
    net = AdjacencyNetworkSpace(space=city_space)
    net.add_node("district-1")
    net.add_connection("district-1", "district-2")         # adjacent_to
    net.add_connection("city", "district-1", "contains_space")

    # Direct zero-copy access to topology:
    sgraph = net.relations    # IS the SpaceRelationGraph

    # Graph Protocol view for a single relation type:
    g = net.as_graph("adjacent_to")   # SpaceRelationGraphAdapter

    # Frozen snapshot for passing to derive_space_relations_from_network:
    ns = net.to_network_space("adjacent_to")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ometeotl_core.model.base import JsonMap, ObjectId, _canonical_json_map
from ometeotl_core.model.space_relations import (
    SPACE_RELATION_TYPES,
    SpaceRelation,
    SpaceRelationGraph,
)
from ometeotl_core.model.spaces import Space

from .graph_kind import UNDIRECTED_SIMPLE, GraphSpec
from .network_space import NetworkSpace
from .relation_graph_adapter import SpaceRelationGraphAdapter


@dataclass
class AdjacencyNetworkSpace:
    """Core Space paired with a SpaceRelationGraph as its topology.

    Attributes:
        space: The underlying ometeotl_core Space object.
        graph_spec: Structural descriptor of this network.
        metadata: Arbitrary key/value annotations.
        _relations: The canonical topology; created fresh in __post_init__.
        _node_ids: Explicitly registered node IDs (allows isolated nodes
            that have no connections yet).

    Proxied properties (read-only, delegate to ``space``):
        id, kind, is_abstract, dimensions
    """

    space: Space
    graph_spec: GraphSpec = field(default=UNDIRECTED_SIMPLE)
    metadata: JsonMap = field(default_factory=dict)
    _relations: SpaceRelationGraph = field(
        init=False, repr=False, default_factory=SpaceRelationGraph
    )
    _node_ids: Set[ObjectId] = field(init=False, repr=False, default_factory=set)

    # ------------------------------------------------------------------
    # Proxy properties — pure delegation
    # ------------------------------------------------------------------

    @property
    def id(self) -> ObjectId:
        return self.space.id

    @property
    def kind(self) -> str:
        return self.space.kind

    @property
    def is_abstract(self) -> bool:
        return self.space.is_abstract

    @property
    def dimensions(self) -> JsonMap:
        return self.space.dimensions

    # ------------------------------------------------------------------
    # Backing store access
    # ------------------------------------------------------------------

    @property
    def relations(self) -> SpaceRelationGraph:
        """The canonical SpaceRelationGraph.

        Direct access is zero-copy and returns the live object.
        Callers who need a full snapshot should use ``to_network_space()``.
        """
        return self._relations

    # ------------------------------------------------------------------
    # Node registration
    # ------------------------------------------------------------------

    def add_node(self, space_id: ObjectId) -> None:
        """Register *space_id* as a node in this network; idempotent."""
        self._node_ids.add(space_id)

    def remove_node(self, space_id: ObjectId) -> None:
        """Remove *space_id* and all its relations; no-op if not present."""
        self._node_ids.discard(space_id)
        # Collect all relations involving space_id before mutating the list.
        to_remove = [
            (r.source_space_id, r.target_space_id, r.relation_type)
            for r in self._relations.relations
            if r.source_space_id == space_id or r.target_space_id == space_id
        ]
        for src, tgt, rel_type in to_remove:
            self._relations.remove_relation(src, tgt, rel_type)

    # ------------------------------------------------------------------
    # Connection mutation
    # ------------------------------------------------------------------

    def add_connection(
        self,
        source: ObjectId,
        target: ObjectId,
        relation_type: str = "adjacent_to",
        metadata: Optional[JsonMap] = None,
    ) -> None:
        """Add a connection between *source* and *target*.

        Delegates to ``SpaceRelationGraph.add_relation()``, which enforces
        all core algebraic constraints.  Propagates any ``ValueError``
        raised by the core (antisymmetry violations, self-loops, unknown
        relation types).

        Args:
            source: Source space ID.
            target: Target space ID.
            relation_type: Must be a key in ``SPACE_RELATION_TYPES``
                (``"adjacent_to"``, ``"contains_space"``,
                ``"intersects_with"``).
            metadata: Optional key/value annotations stored on the
                SpaceRelation (e.g. ``{"weight": 1.5}``).
        """
        self._relations.add_relation(
            SpaceRelation(
                source_space_id=source,
                target_space_id=target,
                relation_type=relation_type,
                metadata=metadata or {},
            )
        )

    def remove_connection(
        self,
        source: ObjectId,
        target: ObjectId,
        relation_type: str = "adjacent_to",
    ) -> None:
        """Remove a connection; no-op if not present."""
        self._relations.remove_relation(source, target, relation_type)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def nodes(self) -> List[ObjectId]:
        """Sorted union of explicitly registered IDs and IDs in relations."""
        ids: set[ObjectId] = set(self._node_ids)
        for r in self._relations.relations:
            ids.add(r.source_space_id)
            ids.add(r.target_space_id)
        return sorted(ids)

    def has_node(self, space_id: ObjectId) -> bool:
        if space_id in self._node_ids:
            return True
        return any(
            r.source_space_id == space_id or r.target_space_id == space_id
            for r in self._relations.relations
        )

    def has_connection(
        self,
        source: ObjectId,
        target: ObjectId,
        relation_type: str = "adjacent_to",
    ) -> bool:
        """O(1) check via SpaceRelationGraph._relation_keys."""
        canonical = SpaceRelation(source, target, relation_type).canonicalize()
        key = (
            canonical.source_space_id,
            canonical.target_space_id,
            canonical.relation_type,
        )
        return key in self._relations._relation_keys

    def neighbors(
        self,
        space_id: ObjectId,
        relation_type: str = "adjacent_to",
    ) -> List[ObjectId]:
        """Sorted neighbours for the given *relation_type*.

        For symmetric types (adjacent_to, intersects_with) returns all
        connected IDs in either direction.  For directed types
        (contains_space) returns out-neighbours only.
        """
        return self.as_graph(relation_type).neighbors(space_id)

    def connections_of(
        self,
        space_id: ObjectId,
        relation_type: Optional[str] = None,
    ) -> List[SpaceRelation]:
        """Return sorted relations originating from *space_id*."""
        return self._relations.relations_from(space_id, relation_type)

    @property
    def node_count(self) -> int:
        return len(self.nodes())

    @property
    def connection_count(self) -> int:
        return len(self._relations.relations)

    # ------------------------------------------------------------------
    # Graph Protocol view and snapshot
    # ------------------------------------------------------------------

    def as_graph(
        self,
        relation_type: str = "adjacent_to",
    ) -> SpaceRelationGraphAdapter:
        """Return a read-only Graph Protocol view filtered to *relation_type*."""
        return SpaceRelationGraphAdapter(
            _relation_graph=self._relations,
            _node_ids=frozenset(self._node_ids),
            _relation_type=relation_type,
        )

    def to_network_space(
        self,
        relation_type: str = "adjacent_to",
    ) -> "NetworkSpace[SpaceRelationGraphAdapter]":
        """Return a frozen NetworkSpace snapshot for *relation_type*.

        Suitable as input to ``derive_space_relations_from_network``
        or any function expecting a ``NetworkSpace[G]``.
        """
        return NetworkSpace(
            space=self.space,
            graph=self.as_graph(relation_type),
            graph_spec=self.graph_spec,
            metadata=dict(self.metadata),
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> JsonMap:
        return {
            "space": self.space.to_dict(),
            "graph_spec": self.graph_spec.to_dict(),
            "node_ids": sorted(self._node_ids),
            "relations": self._relations.to_dict(),
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdjacencyNetworkSpace":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Raises:
            ValueError: If required keys are absent or sub-objects
                cannot be reconstructed.
        """
        try:
            space_data = data["space"]
            graph_spec_data = data["graph_spec"]
        except KeyError as exc:
            raise ValueError(
                f"AdjacencyNetworkSpace.from_dict: missing required key {exc}"
            ) from exc
        ns = cls(
            space=Space.from_dict(space_data),
            graph_spec=GraphSpec.from_dict(graph_spec_data),
            metadata=dict(data.get("metadata") or {}),
        )
        for nid in data.get("node_ids") or []:
            ns.add_node(str(nid))
        for rel_data in (data.get("relations") or {}).get("relations", []):
            ns._relations.add_relation(SpaceRelation.from_dict(rel_data))
        return ns
