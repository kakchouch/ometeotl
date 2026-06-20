"""Graph kind vocabulary for the networks foundations layer.

Mirrors coordinate_system.py in the spatial layer:
- GraphKind is the structural category (directed, undirected, weighted, …)
- GraphSpec is the full descriptor (name + kind + flags)
- Predefined singletons cover the common cases
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Dict, Mapping

JsonMap = Dict[str, Any]


class GraphKind(str, enum.Enum):
    """Broad structural category of a graph.

    Inherits from str so values serialise to their string form without a
    custom encoder.
    """

    UNDIRECTED = "undirected"
    DIRECTED = "directed"
    WEIGHTED_UNDIRECTED = "weighted_undirected"
    WEIGHTED_DIRECTED = "weighted_directed"
    MULTIGRAPH = "multigraph"
    CUSTOM = "custom"


@dataclass(frozen=True)
class GraphSpec:
    """Describes the structural properties of a graph.

    Attributes:
        name: Human-readable identifier (e.g. ``"undirected_simple"``).
        kind: Broad structural category.
        allows_self_loops: Whether the graph allows edges from a node to itself.
    """

    name: str
    kind: GraphKind
    allows_self_loops: bool = False

    def to_dict(self) -> JsonMap:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "allows_self_loops": self.allows_self_loops,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GraphSpec":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Raises:
            ValueError: If required keys are missing or ``kind`` is invalid.
        """
        try:
            name = str(data["name"])
            kind = GraphKind(data["kind"])
        except KeyError as exc:
            raise ValueError(
                f"GraphSpec.from_dict: missing required key {exc}"
            ) from exc
        except ValueError as exc:
            raise ValueError(
                f"GraphSpec.from_dict: invalid 'kind' value: {data.get('kind')!r}"
            ) from exc

        allows_self_loops = bool(data.get("allows_self_loops", False))
        return cls(name=name, kind=kind, allows_self_loops=allows_self_loops)


# ---------------------------------------------------------------------------
# Predefined singletons
# ---------------------------------------------------------------------------

UNDIRECTED_SIMPLE = GraphSpec(
    name="undirected_simple",
    kind=GraphKind.UNDIRECTED,
)
DIRECTED_SIMPLE = GraphSpec(
    name="directed_simple",
    kind=GraphKind.DIRECTED,
)
UNDIRECTED_WEIGHTED = GraphSpec(
    name="undirected_weighted",
    kind=GraphKind.WEIGHTED_UNDIRECTED,
)
DIRECTED_WEIGHTED = GraphSpec(
    name="directed_weighted",
    kind=GraphKind.WEIGHTED_DIRECTED,
)
