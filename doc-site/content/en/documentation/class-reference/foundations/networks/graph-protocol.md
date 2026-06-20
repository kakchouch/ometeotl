---
title: "Graph Protocol"
---

Source:
- [src/ometeotl_foundations/networks/graph.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/graph.py)

Local role:
Structural `Protocol` (PEP 544) that all graph implementations must satisfy. Decorated with `@runtime_checkable` so `isinstance(obj, Graph)` guards work at runtime.

Big-picture role:
The primary adapter extension point between the networks foundations layer and adapter backends. `AdjacencyGraph` satisfies it at the foundations layer; the NetworkX adapter will wrap `networkx.Graph` in a thin class that also satisfies it.

## Type alias

```python
NodeId = str
```

`NodeId` matches `ObjectId` from `ometeotl_core`; nodes correspond to `Space` or object IDs in the core model.

## Protocol members

Properties:
- `is_directed -> bool` — `True` for directed graphs; `False` for undirected
- `node_count -> int` — number of distinct nodes
- `edge_count -> int` — number of edges; undirected graphs count each pair once

Methods:
- `nodes() -> List[NodeId]` — sorted list of all node IDs
- `edges() -> List[Tuple[NodeId, NodeId]]` — sorted list of `(source, target)` pairs; undirected graphs return the canonical `(u, v)` with `u ≤ v`
- `has_node(node_id: NodeId) -> bool`
- `has_edge(source: NodeId, target: NodeId) -> bool`
- `neighbors(node_id: NodeId) -> List[NodeId]` — out-neighbours for directed; all adjacent nodes for undirected; sorted
- `degree(node_id: NodeId) -> int` — out-degree for directed; total degree for undirected
- `to_dict() -> JsonMap` — serialise to a plain dict; the dict **must** include a `"type"` discriminator key so downstream callers can dispatch to the correct `from_dict`

## Design notes

- Path/traversal methods (`shortest_path`, `pagerank`, etc.) are intentionally **not** on the protocol — those are adapter territory.
- Conformance of `AdjacencyGraph` and `SpaceRelationGraphAdapter` is asserted at import time via `assert isinstance(...)`.

Example:

```python
from ometeotl_foundations.networks.adjacency_graph import AdjacencyGraph
from ometeotl_foundations.networks.graph import Graph

g = AdjacencyGraph.create(directed=False)
assert isinstance(g, Graph)   # runtime_checkable

g.add_edge("A", "B")
g.add_edge("B", "C")
assert g.nodes() == ["A", "B", "C"]
assert g.edges() == [("A", "B"), ("B", "C")]
```

See also:
- [AdjacencyGraph](/ometeotl/documentation/class-reference/foundations/networks/adjacency-graph/) — pure-Python implementation
- [SpaceRelationGraphAdapter](/ometeotl/documentation/class-reference/foundations/networks/relation-graph-adapter/) — SpaceRelationGraph-backed implementation
- [GraphBackend Protocol](/ometeotl/documentation/class-reference/foundations/networks/graph-backend-protocol/) — factory interface
