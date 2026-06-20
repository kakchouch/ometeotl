---
title: "GraphKind / GraphSpec / Predefined Singletons"
---

Source:
- [src/ometeotl_foundations/networks/graph_kind.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_foundations/networks/graph_kind.py)

Local role:
Vocabulary for describing the structural category and constraints of a graph, attached to `NetworkSpace` and `AdjacencyNetworkSpace`.

## GraphKind

`str, Enum`. The structural category of a graph. Inherits from `str` so values serialise to their string form without a custom JSON encoder.

Values:
- `UNDIRECTED = "undirected"`
- `DIRECTED = "directed"`
- `WEIGHTED_UNDIRECTED = "weighted_undirected"`
- `WEIGHTED_DIRECTED = "weighted_directed"`
- `MULTIGRAPH = "multigraph"`
- `CUSTOM = "custom"`

## GraphSpec

Frozen dataclass. Describes the structural category and constraints of a graph.

Fields:
- `name: str` — human-readable identifier (e.g. `"undirected_simple"`)
- `kind: GraphKind` — broad structural category
- `allows_self_loops: bool = False` — whether self-loop edges are permitted

Methods:
- `to_dict() -> JsonMap` — serialise to a plain dict
- `@classmethod from_dict(data) -> GraphSpec` — reconstruct from dict; raises `ValueError` on missing or invalid `kind`

## Predefined singletons

| Name | kind | allows_self_loops |
|------|------|-------------------|
| `UNDIRECTED_SIMPLE` | `undirected` | `False` |
| `DIRECTED_SIMPLE` | `directed` | `False` |
| `UNDIRECTED_WEIGHTED` | `weighted_undirected` | `False` |
| `DIRECTED_WEIGHTED` | `weighted_directed` | `False` |

Example:

```python
from ometeotl_foundations.networks.graph_kind import (
    GraphKind, GraphSpec, UNDIRECTED_SIMPLE, DIRECTED_WEIGHTED
)

# Use a predefined singleton
spec = UNDIRECTED_SIMPLE

# Reconstruct from dict (e.g. after JSON deserialisation)
spec2 = GraphSpec.from_dict(spec.to_dict())
assert spec2 == spec

# Custom spec
custom = GraphSpec(
    name="multigraph_with_loops",
    kind=GraphKind.MULTIGRAPH,
    allows_self_loops=True,
)
```

See also:
- [NetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/network-space/)
- [AdjacencyNetworkSpace](/ometeotl/documentation/class-reference/foundations/networks/adjacency-network-space/)
