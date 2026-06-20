---
title: "derive_space_relations_from_network"
---

Source:
- [src/ometeotl_foundations/networks/relation_derivation.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/relation_derivation.py)

Local role:
Bridge function from the networks foundations layer back to `ometeotl_core`. Iterates the edges of any `Graph`-Protocol-compatible network and populates a `SpaceRelationGraph` with the resulting relations.

Big-picture role:
Closes the loop from a concrete graph back to the abstract core model. Mirrors `derive_space_relations()` in the spatial layer. Works identically for any `NetworkSpace[G]` — `AdjacencyGraph`, `SpaceRelationGraphAdapter`, a NetworkX wrapper, or any future `Graph` implementation.

## Signature

```python
def derive_space_relations_from_network(
    network_space: NetworkSpace[G],
    *,
    edge_relation_type: str = "adjacent_to",
    skip_abstract: bool = True,
) -> SpaceRelationGraph:
```

## Algorithm

1. If `skip_abstract` and `network_space.is_abstract` → return an empty `SpaceRelationGraph()` immediately.
2. For each `(source, target)` in `network_space.graph.edges()`:
   - Skip if `source == target` (self-loop guard).
   - Call `result.add_relation(SpaceRelation(source, target, edge_relation_type))`.
3. `SpaceRelationGraph.add_relation()` enforces all core constraints (deduplication, canonicalization, antisymmetry).

No `isinstance` checks. No type switching. Pure `Graph` Protocol usage.

## Parameters

- `network_space` — any object with `is_abstract: bool` and a `graph: G` satisfying the `Graph` Protocol; typically `NetworkSpace[G]`
- `edge_relation_type: str = "adjacent_to"` — must be a key in `SPACE_RELATION_TYPES`; raises `ValueError` if not
- `skip_abstract: bool = True` — when `True`, returns an empty `SpaceRelationGraph` if the space is abstract

## Returns

A `SpaceRelationGraph` populated with one `SpaceRelation` per edge. All algebraic constraints from core are enforced by construction.

## Access patterns for `AdjacencyNetworkSpace`

`AdjacencyNetworkSpace` offers two paths:

```python
# Fast path — zero-copy; returns ALL relation types
sgraph = net.relations

# Explicit path — re-derives from edges; filtered to one relation type
ns = net.to_network_space("adjacent_to")
sgraph = derive_space_relations_from_network(ns)
```

Both produce the same `SpaceRelationGraph` for the given relation type.

Example:

```python
from ometeotl_core.model.spaces import Space
from ometeotl_foundations.networks.adjacency_graph import AdjacencyGraph
from ometeotl_foundations.networks.network_space import NetworkSpace
from ometeotl_foundations.networks.relation_derivation import derive_space_relations_from_network

def make_ns(sid, *edges):
    g = AdjacencyGraph.create(directed=False)
    for u, v in edges:
        g.add_edge(u, v)
    return NetworkSpace(space=Space(id=sid), graph=g)

ns = make_ns("city", ("A", "B"), ("B", "C"))
sgraph = derive_space_relations_from_network(ns)

assert len(sgraph.relations) == 2
assert all(r.relation_type == "adjacent_to" for r in sgraph.relations)

# Custom relation type
ns2 = make_ns("hierarchy", ("parent", "child"))
h = derive_space_relations_from_network(ns2, edge_relation_type="contains_space")
assert h.relations[0].relation_type == "contains_space"
```

See also:
- [NetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/network-space/)
- [AdjacencyNetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/adjacency-network-space/)
- [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
- [Graph Protocol](/ometeotl/documentation/class-reference/foundations/networks/graph-protocol/)
