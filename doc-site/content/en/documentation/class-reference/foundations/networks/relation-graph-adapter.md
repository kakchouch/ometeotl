---
title: "SpaceRelationGraphAdapter"
---

Source:
- [src/ometeotl_foundations/networks/relation_graph_adapter.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/relation_graph_adapter.py)

Local role:
Read-only `Graph` Protocol view of a `SpaceRelationGraph`, filtered to a single relation type. Bridges the core `SpaceRelationGraph` into the networks layer's `Graph` Protocol so that any function expecting a `Graph` can consume a `SpaceRelationGraph` without awareness of the core model.

Big-picture role:
Enables `AdjacencyNetworkSpace.as_graph()` and `to_network_space()` to expose the topology as a `Graph`-Protocol object, making `derive_space_relations_from_network` and any future adapter-agnostic graph algorithm work on `SpaceRelationGraph`-backed data.

Design note: **read-only** — mutation goes through the owning `AdjacencyNetworkSpace`, which delegates to `SpaceRelationGraph.add_relation()` with full constraint enforcement.

## Constructor

```python
SpaceRelationGraphAdapter(
    _relation_graph: SpaceRelationGraph,
    _node_ids: FrozenSet[NodeId] = frozenset(),
    _relation_type: str = "adjacent_to",
)
```

The leading-underscore field names are used as constructor kwargs:

```python
adapter = SpaceRelationGraphAdapter(rg, _relation_type="contains_space")
```

`_node_ids` carries explicitly registered node IDs from the owning `AdjacencyNetworkSpace`, allowing isolated nodes to appear in `nodes()`.

## Directedness

`is_directed` is derived from `SPACE_RELATION_TYPES` at runtime — not stored:

| `_relation_type` | symmetry | `is_directed` |
|------------------|----------|---------------|
| `adjacent_to` | symmetric | `False` |
| `intersects_with` | symmetric | `False` |
| `contains_space` | antisymmetric | `True` |
| unknown type | — | `True` (safe default) |

## Graph Protocol properties

- `is_directed -> bool` — derived from relation type symmetry
- `node_count -> int`
- `edge_count -> int`

## Graph Protocol methods

- `nodes() -> List[NodeId]` — sorted union of `_node_ids` and IDs in filtered relations
- `edges() -> List[Tuple[NodeId, NodeId]]` — sorted; filtered to `_relation_type`
- `has_node(node_id) -> bool`
- `has_edge(source, target) -> bool` — **O(1)** via `SpaceRelationGraph._relation_keys`; symmetric types check both orderings
- `neighbors(node_id) -> List[NodeId]` — for symmetric types collects both directions; for directed types returns out-neighbours only; sorted
- `degree(node_id) -> int`

## Serialisation

- `to_dict() -> JsonMap` — includes `"type": "relation_graph_adapter"`, `"relation_type"`, `"is_directed"`, `"node_ids"`, `"edges"`
- `@classmethod from_dict(data) -> SpaceRelationGraphAdapter` — reconstructs a fresh `SpaceRelationGraph` from the saved edges; raises `ValueError` on wrong type discriminator or missing `"relation_type"`

Example:

```python
from ometeotl_core.model.space_relations import SpaceRelation, SpaceRelationGraph
from ometeotl_foundations.networks.relation_graph_adapter import SpaceRelationGraphAdapter
from ometeotl_foundations.networks.graph import Graph

rg = SpaceRelationGraph()
rg.add_relation(SpaceRelation("A", "B", "adjacent_to"))
rg.add_relation(SpaceRelation("B", "C", "adjacent_to"))

adapter = SpaceRelationGraphAdapter(rg)
assert isinstance(adapter, Graph)        # runtime_checkable
assert not adapter.is_directed           # adjacent_to is symmetric
assert adapter.nodes() == ["A", "B", "C"]
assert adapter.has_edge("B", "A")       # O(1) symmetric lookup

# contains_space is directed
rg2 = SpaceRelationGraph()
rg2.add_relation(SpaceRelation("parent", "child", "contains_space"))
directed_adapter = SpaceRelationGraphAdapter(rg2, _relation_type="contains_space")
assert directed_adapter.is_directed
assert directed_adapter.neighbors("parent") == ["child"]
assert directed_adapter.neighbors("child") == []

# Round-trip
restored = SpaceRelationGraphAdapter.from_dict(adapter.to_dict())
assert restored.edges() == adapter.edges()
```

See also:
- [Graph Protocol](/ometeotl/documentation/class-reference/foundations/networks/graph-protocol/)
- [AdjacencyNetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/adjacency-network-space/)
- [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
