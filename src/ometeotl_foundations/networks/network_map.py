"""NetworkMap: mutable container mapping ObjectId → NetworkExtent.

Mirrors :class:`~ometeotl_foundations.spatial.spatial_map.SpatialMap`
in the spatial layer.  Not generic: all queries are keyed by the string
(network_id, node_id) pair.

Queries are O(n) linear scans.  For large networks the caller can
subclass and override the query methods with an index-backed implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ometeotl_core.model.base import ObjectId

from .graph import NodeId
from .network_extent import NetworkExtent


@dataclass
class NetworkMap:
    """Mutable mapping of object IDs to their network positions.

    Attributes:
        _positions: Internal store; not exposed directly (use accessor methods).
    """

    _positions: Dict[ObjectId, NetworkExtent] = field(
        init=False, repr=False, default_factory=dict
    )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def set_position(self, object_id: ObjectId, extent: NetworkExtent) -> None:
        """Register or replace the network extent for *object_id*."""
        self._positions[object_id] = extent

    def remove_position(self, object_id: ObjectId) -> None:
        """Remove *object_id*; no-op if not present."""
        self._positions.pop(object_id, None)

    def get_position(self, object_id: ObjectId) -> Optional[NetworkExtent]:
        """Return the extent or ``None`` if *object_id* is not registered."""
        return self._positions.get(object_id)

    def all_ids(self) -> List[ObjectId]:
        """Sorted list of all registered object IDs."""
        return sorted(self._positions.keys())

    def as_dict(self) -> Dict[ObjectId, NetworkExtent]:
        """Shallow copy of the internal mapping."""
        return dict(self._positions)

    # ------------------------------------------------------------------
    # Spatial queries — O(n) linear scans
    # ------------------------------------------------------------------

    def objects_at_node(
        self,
        network_id: ObjectId,
        node_id: NodeId,
    ) -> List[ObjectId]:
        """Sorted IDs of objects at *node_id* within *network_id*."""
        return sorted(
            oid
            for oid, ext in self._positions.items()
            if ext.network_id == network_id and ext.node_id == node_id
        )

    def objects_in_network(self, network_id: ObjectId) -> List[ObjectId]:
        """Sorted IDs of all objects registered in *network_id*."""
        return sorted(
            oid for oid, ext in self._positions.items() if ext.network_id == network_id
        )
