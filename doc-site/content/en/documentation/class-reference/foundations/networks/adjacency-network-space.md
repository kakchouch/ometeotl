---
title: "AdjacencyNetworkSpace"
---

Source:
- [src/ometeotl_foundations/networks/adjacency_network_space.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/adjacency_network_space.py)

Local role:
Ready-to-use mutable foundations-layer class that pairs a core `Space` with a `SpaceRelationGraph` as its topology. The primary class for building and querying network structures at the foundations layer.

Big-picture role:
`AdjacencyNetworkSpace._relations: SpaceRelationGraph` IS the topology — the single canonical source of truth. `add_connection()` delegates to `SpaceRelationGraph.add_relation()`, which enforces all algebraic constraints from `ometeotl_core` (symmetric canonicalization, antisymmetry, no self-loops, deduplication). There is no separate graph object that can drift out of sync.

Design principle: **composition over inheritance** — `AdjacencyNetworkSpace` wraps `Space`, keeping `ometeotl_core` untouched. Analogous to `GeometricSpace` in the spatial layer, but mutable because network topologies evolve over time.

## Fields

- `space: Space` — the underlying core `Space` object
- `graph_spec: GraphSpec = UNDIRECTED_SIMPLE` — structural descriptor of this network
- `metadata: JsonMap = {}` — arbitrary key/value annotations
- `_relations: SpaceRelationGraph` — canonical topology; created fresh on construction
- `_node_ids: Set[ObjectId]` — explicitly registered node IDs; allows isolated nodes before any connections

## Proxy properties (delegate to `space`)

- `id -> ObjectId`
- `kind -> str`
- `is_abstract -> bool`
- `dimensions -> JsonMap`

## Backing store access

- `relations -> SpaceRelationGraph` — the canonical `SpaceRelationGraph`; direct access is **zero-copy** and returns the live object

## Node registration

- `add_node(space_id: ObjectId) -> None` — idempotent; registers a node without requiring a connection
- `remove_node(space_id: ObjectId) -> None` — removes the node from `_node_ids` and removes all relations involving `space_id`; no-op if absent

## Connection mutation

- `add_connection(source, target, relation_type="adjacent_to", metadata=None) -> None` — delegates to `SpaceRelationGraph.add_relation()`; propagates all `ValueError` from core (antisymmetry violations, self-loops, unknown relation types)
- `remove_connection(source, target, relation_type="adjacent_to") -> None` — no-op if not present

## Query methods

- `nodes() -> List[ObjectId]` — sorted union of `_node_ids` and all IDs in `_relations`
- `has_node(space_id) -> bool`
- `has_connection(source, target, relation_type="adjacent_to") -> bool` — **O(1)** via `SpaceRelationGraph._relation_keys`
- `neighbors(space_id, relation_type="adjacent_to") -> List[ObjectId]` — delegates to `as_graph().neighbors()`; sorted
- `connections_of(space_id, relation_type=None) -> List[SpaceRelation]` — all relations from `space_id`; filtered by type if provided
- `node_count -> int` (property)
- `connection_count -> int` (property)

## Graph Protocol views

- `as_graph(relation_type="adjacent_to") -> SpaceRelationGraphAdapter` — read-only `Graph` Protocol view filtered to one relation type
- `to_network_space(relation_type="adjacent_to") -> NetworkSpace[SpaceRelationGraphAdapter]` — frozen snapshot for passing to `derive_space_relations_from_network` or any function expecting `NetworkSpace[G]`

## Serialisation

- `to_dict() -> JsonMap` — saves `space`, `graph_spec`, `node_ids`, `relations`, `metadata`
- `@classmethod from_dict(data) -> AdjacencyNetworkSpace` — raises `ValueError` on missing required keys

Example:

```python
from ometeotl_core.model.spaces import Space
from ometeotl_foundations.networks.adjacency_network_space import AdjacencyNetworkSpace

space = Space(id="city-map")
net = AdjacencyNetworkSpace(space=space)

# Isolated node (no connections yet)
net.add_node("district-0")

# Connections enforce core algebraic constraints
net.add_connection("district-1", "district-2")          # adjacent_to
net.add_connection("city", "district-1", "contains_space")

assert net.nodes() == ["city", "district-0", "district-1", "district-2"]
assert net.has_connection("district-2", "district-1")   # O(1) symmetric
assert net.neighbors("district-1") == ["district-2"]    # adjacent_to, undirected

# Direct access to topology (zero-copy)
sgraph = net.relations   # IS the SpaceRelationGraph

# Graph Protocol view
g = net.as_graph("adjacent_to")
assert not g.is_directed

# Frozen snapshot for derive_space_relations_from_network
ns = net.to_network_space("adjacent_to")

# Round-trip
restored = AdjacencyNetworkSpace.from_dict(net.to_dict())
assert restored.has_connection("district-1", "district-2")
```

See also:
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
- [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
- [SpaceRelationGraphAdapter](/ometeotl/documentation/class-reference/foundations/networks/relation-graph-adapter/)
- [NetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/network-space/)
- [derive_space_relations_from_network](/ometeotl/documentation/class-reference/foundations/networks/relation-derivation/)
