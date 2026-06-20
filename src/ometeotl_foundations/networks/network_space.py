"""NetworkSpace[G]: frozen generic composition of a Space and a graph.

Mirrors :class:`~ometeotl_foundations.spatial.geometric_space.GeometricSpace`
in the spatial layer:
- ``GeometricSpace[G]`` pairs a core Space with a concrete geometry.
- ``NetworkSpace[G]`` pairs a core Space with a concrete graph.

This is the **adapter extension point**: the NetworkX adapter produces
``NetworkSpace[NetworkXGraph]`` where ``NetworkXGraph`` satisfies the
``Graph`` Protocol.

``AdjacencyNetworkSpace`` uses this as a snapshot type:
``to_network_space()`` returns a ``NetworkSpace[SpaceRelationGraphAdapter]``
that callers can pass to ``derive_space_relations_from_network``.

Design notes:
- Frozen: graph snapshots are value objects; adapters that need a mutable
  class define their own (e.g. ``NetworkXNetworkSpace``).
- Serialisation requires an injected ``graph_deserializer`` because
  reconstructing ``G`` is adapter-specific.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Mapping, TypeVar

from ometeotl_core.model.base import JsonMap, ObjectId, _canonical_json_map
from ometeotl_core.model.spaces import Space

from .graph_kind import UNDIRECTED_SIMPLE, GraphSpec

G = TypeVar("G")


@dataclass(frozen=True)
class NetworkSpace(Generic[G]):
    """A core Space paired with a concrete graph.

    Attributes:
        space: The underlying ometeotl_core Space object.
        graph: The graph describing the network topology of the space.
            Must satisfy the
            :class:`~ometeotl_foundations.networks.graph.Graph` protocol.
        graph_spec: The structural descriptor of *graph*.
        metadata: Arbitrary key/value annotations.

    Proxied properties (read-only, delegate to ``space``):
        id, kind, is_abstract, dimensions
    """

    space: Space
    graph: G
    graph_spec: GraphSpec = field(default=UNDIRECTED_SIMPLE)
    metadata: JsonMap = field(default_factory=dict)

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
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> JsonMap:
        """Serialise to a plain dict.

        The ``graph`` entry is produced by ``self.graph.to_dict()``,
        which must include a ``"type"`` discriminator key.
        """
        graph_serialisable: Any = self.graph
        return {
            "space": self.space.to_dict(),
            "graph": graph_serialisable.to_dict(),
            "graph_spec": self.graph_spec.to_dict(),
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
        graph_deserializer: Callable[[JsonMap], G],
    ) -> "NetworkSpace[G]":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Args:
            data: The serialised representation.
            graph_deserializer: A callable that reconstructs the graph
                from its ``JsonMap`` representation.  Pass
                ``AdjacencyGraph.from_dict`` at the foundations layer,
                or an adapter-specific deserialiser otherwise.

        Raises:
            ValueError: If required keys are absent or sub-objects
                cannot be reconstructed.
        """
        raw_metadata = data.get("metadata") or {}
        return cls(
            space=Space.from_dict(data["space"]),
            graph=graph_deserializer(data["graph"]),
            graph_spec=GraphSpec.from_dict(data["graph_spec"]),
            metadata=dict(raw_metadata),
        )
