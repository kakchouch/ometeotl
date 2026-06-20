---
title: "AdjacencyGraph"
---

Source:
- [src/ometeotl_foundations/networks/adjacency_graph.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/adjacency_graph.py)

Local role:
Standalone pure-Python mutable graph that satisfies the `Graph` Protocol. The foundations-layer graph primitive — used when a graph is needed independently of a `Space` (e.g. intermediate computation, adapter input via `GraphBackend.make_from_adjacency`).

Big-picture role:
Not coupled to `SpaceRelationGraph` or any Space concept. Used as the backing type for `NetworkSpace[AdjacencyGraph]` when a generic mutable graph is needed. Adapter backends use it as a portable interchange format via `GraphBackend.make_from_adjacency`.

Design principle: **no spatial coupling** — `AdjacencyGraph` knows nothing about `Space` or `SpaceRelation`. For Space-coupled network topology, use `AdjacencyNetworkSpace`.

## Named constructor

```python
AdjacencyGraph.create(directed: bool = False) -> AdjacencyGraph
```

Prefer this over the dataclass constructor `AdjacencyGraph(_directed=True)` — the leading underscore in the field name signals that it is not a public API.

## Fields (internal)

- `_directed: bool` — set at construction time; cannot be changed afterwards
- `_adj: Dict[NodeId, Dict[NodeId, float]]` — adjacency dict; undirected graphs store the canonical `(u, v)` with `u ≤ v` form
- `_node_meta: Dict[NodeId, Dict[str, Any]]` — per-node metadata (stored separately from edge weights)

## Graph Protocol properties

- `is_directed -> bool`
- `node_count -> int` — number of distinct nodes
- `edge_count -> int` — undirected: counts canonical `u ≤ v` pairs; directed: total outgoing edges

## Graph Protocol methods

- `nodes() -> List[NodeId]` — sorted
- `edges() -> List[Tuple[NodeId, NodeId]]` — sorted; undirected returns canonical `(u, v)` with `u ≤ v`
- `has_node(node_id) -> bool`
- `has_edge(source, target) -> bool` — undirected: checks both orderings
- `neighbors(node_id) -> List[NodeId]` — out-neighbours (directed) or all adjacent nodes (undirected); sorted
- `degree(node_id) -> int` — out-degree (directed) or total degree (undirected)

## Mutation methods

- `add_node(node_id, metadata=None) -> None` — idempotent; attaches optional metadata dict
- `remove_node(node_id) -> None` — removes the node and all its incident edges; no-op if absent
- `add_edge(source, target, weight=1.0) -> None` — auto-creates nodes if absent; undirected stores canonical `u ≤ v`
- `remove_edge(source, target) -> None` — no-op if not present

## Convenience methods (not on Graph Protocol)

- `get_edge_weight(source, target) -> Optional[float]` — `None` if the edge does not exist; undirected respects canonical direction
- `get_node_metadata(node_id) -> Dict[str, Any]` — returns a copy; empty dict if no metadata was set

## Serialisation

- `to_dict() -> JsonMap` — includes `"type": "adjacency_graph"`, `"directed": bool`, `"nodes": {id: meta}`, `"edges": [[u, v, weight], …]`
- `@classmethod from_dict(data) -> AdjacencyGraph` — raises `ValueError` if the `"type"` discriminator is wrong

Example:

```python
from ometeotl_foundations.networks.adjacency_graph import AdjacencyGraph
from ometeotl_foundations.networks.graph import Graph

# Undirected graph
g = AdjacencyGraph.create(directed=False)
g.add_node("A", metadata={"label": "depot"})
g.add_edge("A", "B", weight=2.5)
g.add_edge("B", "C")

assert g.nodes() == ["A", "B", "C"]
assert g.edges() == [("A", "B"), ("B", "C")]
assert g.neighbors("B") == ["A", "C"]   # undirected
assert g.get_edge_weight("A", "B") == 2.5
assert isinstance(g, Graph)             # runtime_checkable

# Directed graph
dg = AdjacencyGraph.create(directed=True)
dg.add_edge("X", "Y")
dg.add_edge("Y", "Z")
assert dg.neighbors("Y") == ["Z"]      # out-neighbours only

# Round-trip
restored = AdjacencyGraph.from_dict(g.to_dict())
assert restored.edges() == g.edges()
```

See also:
- [Graph Protocol](/ometeotl/documentation/class-reference/foundations/networks/graph-protocol/)
- [NetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/network-space/)
- [AdjacencyNetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/adjacency-network-space/)
- [GraphBackend Protocol](/ometeotl/documentation/class-reference/foundations/networks/graph-backend-protocol/)
