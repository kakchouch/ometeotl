---
title: "NetworkSpace"
---

Source:
- [src/ometeotl_foundations/networks/network_space.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/network_space.py)

Local role:
Frozen generic dataclass that composes a core `Space` with a concrete graph. The adapter extension point for the networks layer — mirrors `GeometricSpace[G]` in the spatial layer.

Big-picture role:
`NetworkSpace[G]` answers both ontological questions (kind, is_abstract, dimensions) and network questions (graph topology) through a single object, without touching the `Space` dataclass directly. It is the input type for `derive_space_relations_from_network()`.

Design principle: **composition over inheritance** — `NetworkSpace` wraps `Space` rather than subclassing it, keeping `ometeotl_core` untouched.

## Type parameter

`G` — the concrete graph type (e.g. `AdjacencyGraph`, `SpaceRelationGraphAdapter`, or a NetworkX wrapper). Must satisfy the `Graph` Protocol.

## Fields

- `space: Space` — the underlying core `Space` object
- `graph: G` — the graph describing the network topology of the space
- `graph_spec: GraphSpec = UNDIRECTED_SIMPLE` — structural descriptor of `graph`
- `metadata: JsonMap = {}` — arbitrary key/value annotations

Frozen — a network space is a value object. Network mutations go through `AdjacencyNetworkSpace`; `NetworkSpace[G]` is for snapshots and adapter-backed read-only views.

## Proxy properties (delegate to `space`, no logic duplication)

- `id -> ObjectId` — identifier of the underlying space
- `kind -> str` — kind of the underlying space
- `is_abstract -> bool` — whether the underlying space is non-canonical
- `dimensions -> JsonMap` — dimension map of the underlying space

## Serialisation

- `to_dict() -> JsonMap` — self-contained; calls `graph.to_dict()` (requires `"type"` discriminator in the result)
- `@classmethod from_dict(data, graph_deserializer: Callable[[JsonMap], G]) -> NetworkSpace[G]` — injected deserializer pattern; pass `AdjacencyGraph.from_dict` at the foundations layer, or an adapter-specific deserializer otherwise; raises `ValueError` on missing required keys

The injected deserializer makes `from_dict` adapter-agnostic: the caller controls how `G` is reconstructed.

Example:

```python
from ometeotl_core.model.spaces import Space
from ometeotl_foundations.networks.adjacency_graph import AdjacencyGraph
from ometeotl_foundations.networks.network_space import NetworkSpace
from ometeotl_foundations.networks.graph_kind import UNDIRECTED_SIMPLE

space = Space(id="city-network")
g = AdjacencyGraph.create(directed=False)
g.add_edge("district-1", "district-2")
g.add_edge("district-2", "district-3")

ns = NetworkSpace(
    space=space,
    graph=g,
    graph_spec=UNDIRECTED_SIMPLE,
    metadata={"source": "planning-dept"},
)

assert ns.id == "city-network"
assert ns.graph.nodes() == ["district-1", "district-2", "district-3"]

# Round-trip
d = ns.to_dict()
restored = NetworkSpace.from_dict(d, AdjacencyGraph.from_dict)
assert restored.graph.edges() == ns.graph.edges()
```

See also:
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
- [AdjacencyGraph](/ometeotl/documentation/class-reference/foundations/networks/adjacency-graph/)
- [AdjacencyNetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/adjacency-network-space/)
- [derive_space_relations_from_network](/ometeotl/documentation/class-reference/foundations/networks/relation-derivation/)
