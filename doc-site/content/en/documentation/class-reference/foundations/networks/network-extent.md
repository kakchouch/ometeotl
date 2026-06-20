---
title: "NetworkExtent"
---

Source:
- [src/ometeotl_foundations/networks/network_extent.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/network_extent.py)

Local role:
Frozen value object recording where a non-space object (actor, resource, etc.) sits within a named network — specifically, which node of which network it occupies.

Big-picture role:
Distinct from `AdjacencyNetworkSpace`:
- **`AdjacencyNetworkSpace`** describes the topology of a *network space* itself.
- **`NetworkExtent`** describes where an *object* IS within a network — at a specific node.

`NetworkMap` maps `ObjectId → NetworkExtent` to track actor and resource positions in networks.

Mirrors `SpatialExtent` in the spatial layer.

## Fields

- `network_id: ObjectId` — loose reference (by ID string) to the `AdjacencyNetworkSpace` or `NetworkSpace` that defines the topology; keeps `NetworkExtent` lightweight with no hard dependency on the network collection
- `node_id: NodeId` — the node within the network where the object is located
- `metadata: JsonMap = {}` — arbitrary key/value annotations

Frozen — mutations create a new `NetworkExtent`.

## Serialisation

- `to_dict() -> JsonMap`
- `@classmethod from_dict(data) -> NetworkExtent` — raises `KeyError` on missing required fields

Example:

```python
from ometeotl_foundations.networks.network_extent import NetworkExtent

actor_extent = NetworkExtent(
    network_id="city-map",
    node_id="district-1",
    metadata={"role": "patrol"},
)

assert actor_extent.network_id == "city-map"
assert actor_extent.node_id == "district-1"

# Round-trip
restored = NetworkExtent.from_dict(actor_extent.to_dict())
assert restored == actor_extent
```

See also:
- [NetworkMap](/ometeotl/documentation/class-reference/foundations/networks/network-map/)
- [AdjacencyNetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/adjacency-network-space/)
