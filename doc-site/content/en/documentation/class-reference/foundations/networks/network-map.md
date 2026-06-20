---
title: "NetworkMap"
---

Source:
- [src/ometeotl_foundations/networks/network_map.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/network_map.py)

Local role:
Mutable container mapping `ObjectId → NetworkExtent`. Tracks where actors, resources, and other non-space objects are positioned within network spaces.

Big-picture role:
Mirrors `SpatialMap` in the spatial layer. Lets callers ask "which node is actor X at?" and "which actors are at node Y in network Z?" without coupling those queries to the network topology itself.

## Mutation methods

- `set_position(object_id: ObjectId, extent: NetworkExtent) -> None` — add or replace a position record
- `remove_position(object_id: ObjectId) -> None` — no-op if not present

## Query methods

- `get_position(object_id: ObjectId) -> Optional[NetworkExtent]` — `None` if not registered
- `all_ids() -> List[ObjectId]` — sorted list of all registered object IDs
- `as_dict() -> Dict[ObjectId, NetworkExtent]` — shallow copy of the internal mapping
- `objects_at_node(network_id: ObjectId, node_id: NodeId) -> List[ObjectId]` — sorted; **O(n)** scan
- `objects_in_network(network_id: ObjectId) -> List[ObjectId]` — sorted; **O(n)** scan

## Performance note

`objects_at_node` and `objects_in_network` scan all registered positions. For large maps with frequent positional queries, consider maintaining inverse indexes at the application layer.

Example:

```python
from ometeotl_foundations.networks.network_map import NetworkMap
from ometeotl_foundations.networks.network_extent import NetworkExtent

nmap = NetworkMap()

nmap.set_position("actor-1", NetworkExtent(network_id="city-map", node_id="district-1"))
nmap.set_position("actor-2", NetworkExtent(network_id="city-map", node_id="district-2"))
nmap.set_position("actor-3", NetworkExtent(network_id="city-map", node_id="district-1"))

assert nmap.get_position("actor-1").node_id == "district-1"
assert nmap.objects_at_node("city-map", "district-1") == ["actor-1", "actor-3"]
assert nmap.objects_in_network("city-map") == ["actor-1", "actor-2", "actor-3"]

nmap.remove_position("actor-2")
assert nmap.all_ids() == ["actor-1", "actor-3"]
```

See also:
- [NetworkExtent](/ometeotl/documentation/class-reference/foundations/networks/network-extent/)
- [AdjacencyNetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/adjacency-network-space/)
