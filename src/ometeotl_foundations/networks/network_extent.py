"""NetworkExtent: where a non-space object sits in a network.

Mirrors :class:`~ometeotl_foundations.spatial.spatial_extent.SpatialExtent`
in the spatial layer.  Not generic: position in a network is always a
``NodeId`` string (node identity suffices, weights are on edges).

``NetworkMap`` maps ``ObjectId → NetworkExtent`` to track which node
an actor or resource occupies within a given network.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from ometeotl_core.model.base import JsonMap, ObjectId, _canonical_json_map

from .graph import NodeId


@dataclass(frozen=True)
class NetworkExtent:
    """Records where an object is located within a named network.

    Attributes:
        network_id: ID of the ``AdjacencyNetworkSpace`` or ``NetworkSpace``
            that defines the network.  Kept as a loose string reference
            (no hard dependency on the space collection).
        node_id: The node within the network at which the object resides.
        metadata: Arbitrary key/value annotations.
    """

    network_id: ObjectId
    node_id: NodeId
    metadata: JsonMap = field(default_factory=dict)

    def to_dict(self) -> JsonMap:
        return {
            "network_id": self.network_id,
            "node_id": self.node_id,
            "metadata": _canonical_json_map(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NetworkExtent":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Raises:
            KeyError: If required keys are missing.
        """
        return cls(
            network_id=str(data["network_id"]),
            node_id=str(data["node_id"]),
            metadata=dict(data.get("metadata") or {}),
        )
