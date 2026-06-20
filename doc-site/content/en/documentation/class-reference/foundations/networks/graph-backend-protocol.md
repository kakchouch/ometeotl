---
title: "GraphBackend Protocol"
---

Source:
- [src/ometeotl_foundations/networks/graph_backend.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/graph_backend.py)

Local role:
Structural `Protocol` (PEP 544) that adapter-layer graph factories must satisfy. It is the second adapter extension point alongside the `Graph` Protocol.

Big-picture role:
`GraphBackend` decouples graph construction from graph consumption. A foundations-layer caller that needs a new graph calls `backend.make_graph()`; the backend decides whether to produce an `AdjacencyGraph` or a `networkx.Graph` wrapper. The caller never imports a library-specific constructor.

## Protocol members

- `make_graph(directed: bool = False) -> Graph` — create an empty graph
- `make_from_edges(edges: List[Tuple[NodeId, NodeId, float]], directed: bool = False) -> Graph` — create a graph pre-populated with weighted edges; `float` is the edge weight
- `make_from_adjacency(adj: AdjacencyGraph) -> Graph` — convert an `AdjacencyGraph` into the backend's native representation (e.g. a `networkx.Graph`)

## Design notes

- `@runtime_checkable` — `isinstance(obj, GraphBackend)` works at runtime.
- No `GraphBackend` implementation exists at the foundations layer; this is intentionally left for adapters.
- Analogous to `SpatialBackend` in the spatial layer.

See also:
- [Graph Protocol](/ometeotl/documentation/class-reference/foundations/networks/graph-protocol/)
- [AdjacencyGraph](/ometeotl/documentation/class-reference/foundations/networks/adjacency-graph/)
