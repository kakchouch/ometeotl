"""Coordinate value types for the spatial foundations layer.

These are pure, immutable value objects with no geometry logic.
Arithmetic, distance, and projection belong to Geometry implementations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinate2D:
    """A position in a flat 2-D Cartesian or projected plane."""

    x: float
    y: float


@dataclass(frozen=True)
class Coordinate3D:
    """A position in a 3-D Cartesian space."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class GeoCoordinate:
    """A geographic position expressed as longitude / latitude (GeoJSON convention).

    Validates ranges on construction:
    - longitude: [-180, 180]
    - latitude:  [-90, 90]
    """

    longitude: float
    latitude: float
    altitude: float = 0.0

    def __post_init__(self) -> None:
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"longitude must be in [-180, 180], got {self.longitude}")
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"latitude must be in [-90, 90], got {self.latitude}")


@dataclass(frozen=True)
class GridCell:
    """A discrete position in a tile/hex grid.

    col and row may be negative (valid in world-coordinate grids).
    layer defaults to 0 for 2-D grids.
    """

    col: int
    row: int
    layer: int = 0
