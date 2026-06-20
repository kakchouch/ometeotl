---
title: "Foundations / Networks"
description: "Class reference for ometeotl_foundations/networks — pure-Python graph-theory specialization layer"
---

Source:
- [src/ometeotl_foundations/networks/](https://github.com/kakchouch/ometeotl/tree/main/src/ometeotl_foundations/networks/)

## Purpose

`ometeotl_foundations/networks/` is the first-order graph-theory specialization of `ometeotl_core`. It provides a `Graph` Protocol, graph vocabulary types, a pure-Python mutable graph primitive, a `SpaceRelationGraph`-backed adapter, and generic typed network containers — all in pure Python with no library dependency. A NetworkX-backed adapter (`ometeotl_adapters/networks_networkx/`) will implement the same protocols for production graph algorithms.

## Layer role in the three-tier architecture

```
ometeotl_core          — abstract model (Space, SpaceRelationGraph, …)
ometeotl_foundations   — first-order specialization (this layer)
ometeotl_adapters      — library-backed implementations (NetworkX, …)
```

## Consistency guarantee

`AdjacencyNetworkSpace._relations: SpaceRelationGraph` IS the topology — the single canonical source of truth. `add_connection()` delegates to `SpaceRelationGraph.add_relation()`, which enforces all algebraic constraints defined in `ometeotl_core` (symmetric canonicalization, antisymmetry, no self-loops, deduplication). There is no separate graph object that can drift out of sync.

## Adapter extension model

The adapter extension pattern mirrors the spatial layer exactly:

| Spatial | Networks |
|---------|----------|
| `Geometry` Protocol | `Graph` Protocol |
| `SpatialBackend` Protocol | `GraphBackend` Protocol |
| `GeometricSpace[G]` | `NetworkSpace[G]` |
| `BoundingBox` | `AdjacencyGraph` |
| Shapely adapter | NetworkX adapter |

A NetworkX adapter wraps `networkx.Graph` in a thin `NetworkXGraph: Graph` class. `derive_space_relations_from_network(NetworkSpace[NetworkXGraph])` works unchanged — the foundations layer never needs to know about NetworkX.

## Public surface

| File | Exports |
|------|---------|
| `graph_kind.py` | `GraphKind`, `GraphSpec`, `UNDIRECTED_SIMPLE`, `DIRECTED_SIMPLE`, `UNDIRECTED_WEIGHTED`, `DIRECTED_WEIGHTED` |
| `graph.py` | `Graph` (Protocol), `NodeId` |
| `graph_backend.py` | `GraphBackend` (Protocol) |
| `adjacency_graph.py` | `AdjacencyGraph` |
| `relation_graph_adapter.py` | `SpaceRelationGraphAdapter` |
| `network_space.py` | `NetworkSpace[G]` |
| `adjacency_network_space.py` | `AdjacencyNetworkSpace` |
| `network_extent.py` | `NetworkExtent` |
| `network_map.py` | `NetworkMap` |
| `relation_derivation.py` | `derive_space_relations_from_network()` |
| `spatial_bridge.py` | `build_proximity_network()` *(explicit import only — not in `__init__.py`)* |

## Pages in this section

- [GraphKind / GraphSpec / predefined singletons](/ometeotl/documentation/class-reference/foundations/networks/graph-kind/)
- [Graph Protocol](/ometeotl/documentation/class-reference/foundations/networks/graph-protocol/)
- [GraphBackend Protocol](/ometeotl/documentation/class-reference/foundations/networks/graph-backend-protocol/)
- [AdjacencyGraph](/ometeotl/documentation/class-reference/foundations/networks/adjacency-graph/)
- [SpaceRelationGraphAdapter](/ometeotl/documentation/class-reference/foundations/networks/relation-graph-adapter/)
- [NetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/network-space/)
- [AdjacencyNetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/adjacency-network-space/)
- [NetworkExtent](/ometeotl/documentation/class-reference/foundations/networks/network-extent/)
- [NetworkMap](/ometeotl/documentation/class-reference/foundations/networks/network-map/)
- [derive_space_relations_from_network](/ometeotl/documentation/class-reference/foundations/networks/relation-derivation/)
