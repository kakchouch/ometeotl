"""Coordinate system vocabulary for the spatial foundations layer."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

JsonMap = Dict[str, Any]


class CoordinateKind(str, enum.Enum):
    """Nature of a coordinate system.

    Inherits from str so values serialise to their string form without a
    custom encoder (e.g. ``json.dumps({"kind": CoordinateKind.CARTESIAN})``
    produces ``'{"kind": "cartesian"}'``).
    """

    CARTESIAN = "cartesian"
    GEOGRAPHIC = "geographic"
    GRID = "grid"
    CUSTOM = "custom"


@dataclass(frozen=True)
class CoordinateSystem:
    """Describes the coordinate frame used by a geometry or extent.

    Attributes:
        name: Human-readable identifier (e.g. ``"wgs84"``).
        kind: Broad category of the coordinate system.
        unit: Native unit of measure (``"meter"``, ``"degree"``, ``"cell"``).
        srid: EPSG code for geographic / projected systems (optional).
    """

    name: str
    kind: CoordinateKind
    unit: str
    srid: Optional[int] = None

    def to_dict(self) -> JsonMap:
        """Serialise to a plain dict suitable for JSON storage."""
        result: JsonMap = {
            "name": self.name,
            "kind": self.kind.value,
            "unit": self.unit,
        }
        if self.srid is not None:
            result["srid"] = self.srid
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CoordinateSystem":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Raises:
            ValueError: If required keys are missing or ``kind`` is invalid.
        """
        try:
            name = str(data["name"])
            kind = CoordinateKind(data["kind"])
            unit = str(data["unit"])
        except KeyError as exc:
            raise ValueError(
                f"CoordinateSystem.from_dict: missing required key {exc}"
            ) from exc
        except ValueError as exc:
            raise ValueError(
                f"CoordinateSystem.from_dict: invalid 'kind' value: {data.get('kind')!r}"
            ) from exc

        srid_raw = data.get("srid")
        srid = int(srid_raw) if srid_raw is not None else None
        return cls(name=name, kind=kind, unit=unit, srid=srid)


# ---------------------------------------------------------------------------
# Predefined singletons
# ---------------------------------------------------------------------------

CARTESIAN_2D = CoordinateSystem(
    name="cartesian_2d", kind=CoordinateKind.CARTESIAN, unit="meter"
)
CARTESIAN_3D = CoordinateSystem(
    name="cartesian_3d", kind=CoordinateKind.CARTESIAN, unit="meter"
)
WGS84 = CoordinateSystem(
    name="wgs84", kind=CoordinateKind.GEOGRAPHIC, unit="degree", srid=4326
)
GRID = CoordinateSystem(name="grid", kind=CoordinateKind.GRID, unit="cell")
