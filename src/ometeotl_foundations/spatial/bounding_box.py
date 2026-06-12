"""BoundingBox: pure-Python implementation of the Geometry protocol.

BoundingBox is an axis-aligned bounding box (AABB). It is the only
geometry implementation provided at the foundations layer, so the entire
spatial module is testable and usable without a library adapter.

Design notes:
- ``contains`` / ``intersects`` / ``touches`` / ``distance`` are only
  fully correct when both operands are BoundingBox instances.  When
  *other* is a different concrete type, these methods fall back to
  comparing AABB bounds (``other.bounds``), which is always a
  BoundingBox.  This fallback is documented on each method.
- All operations that produce a new geometry return a new BoundingBox;
  the original is never mutated (frozen dataclass).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping

from .coordinates import Coordinate2D
from .geometry import Geometry

JsonMap = Dict[str, Any]

_BOUNDING_BOX_TYPE = "bounding_box"


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box implementing the Geometry protocol.

    Attributes:
        min_x: Left boundary.
        min_y: Bottom boundary.
        max_x: Right boundary.
        max_y: Top boundary.

    Raises:
        ValueError: If ``min_x > max_x`` or ``min_y > max_y``.
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def __post_init__(self) -> None:
        if self.min_x > self.max_x:
            raise ValueError(f"min_x ({self.min_x}) must be <= max_x ({self.max_x})")
        if self.min_y > self.max_y:
            raise ValueError(f"min_y ({self.min_y}) must be <= max_y ({self.max_y})")

    # ------------------------------------------------------------------
    # Geometry protocol — properties
    # ------------------------------------------------------------------

    @property
    def area(self) -> float:
        """Area of the box. Zero for degenerate (point or line) boxes."""
        return (self.max_x - self.min_x) * (self.max_y - self.min_y)

    @property
    def centroid(self) -> Coordinate2D:
        """Centre of the box."""
        return Coordinate2D(
            x=(self.min_x + self.max_x) / 2.0,
            y=(self.min_y + self.max_y) / 2.0,
        )

    @property
    def bounds(self) -> "BoundingBox":
        """A BoundingBox is its own bounding box."""
        return self

    # ------------------------------------------------------------------
    # Geometry protocol — predicate methods
    # ------------------------------------------------------------------

    def contains(self, other: Geometry) -> bool:
        """Return True if this box fully contains *other*.

        When *other* is not a BoundingBox, the comparison falls back to
        ``other.bounds`` (always a BoundingBox).  This means the result
        is based on bounding-box approximation, not exact containment.
        """
        b = other if isinstance(other, BoundingBox) else other.bounds
        return (
            self.min_x <= b.min_x
            and self.min_y <= b.min_y
            and self.max_x >= b.max_x
            and self.max_y >= b.max_y
        )

    def intersects(self, other: Geometry) -> bool:
        """Return True if this box shares any interior area with *other*.

        Falls back to ``other.bounds`` for non-BoundingBox operands.
        """
        b = other if isinstance(other, BoundingBox) else other.bounds
        return not (
            b.min_x > self.max_x
            or b.max_x < self.min_x
            or b.min_y > self.max_y
            or b.max_y < self.min_y
        )

    def touches(self, other: Geometry) -> bool:
        """Return True if the boxes share a boundary but not interior area.

        Falls back to ``other.bounds`` for non-BoundingBox operands.
        """
        b = other if isinstance(other, BoundingBox) else other.bounds
        # They touch if they intersect (share at least one edge/corner)
        # but do NOT have overlapping interiors.
        share_boundary = (
            b.min_x == self.max_x
            or b.max_x == self.min_x
            or b.min_y == self.max_y
            or b.max_y == self.min_y
        )
        return share_boundary and not (
            b.min_x > self.max_x
            or b.max_x < self.min_x
            or b.min_y > self.max_y
            or b.max_y < self.min_y
        )

    def distance(self, other: Geometry) -> float:
        """Minimum Euclidean distance to *other*; 0.0 if they overlap.

        Falls back to ``other.bounds`` for non-BoundingBox operands.
        """
        b = other if isinstance(other, BoundingBox) else other.bounds
        dx = max(0.0, b.min_x - self.max_x, self.min_x - b.max_x)
        dy = max(0.0, b.min_y - self.max_y, self.min_y - b.max_y)
        return math.sqrt(dx * dx + dy * dy)

    # ------------------------------------------------------------------
    # Convenience — not on Geometry protocol
    # ------------------------------------------------------------------

    def contains_point(self, point: Coordinate2D) -> bool:
        """Return True if *point* lies inside or on the boundary of this box."""
        return (
            self.min_x <= point.x <= self.max_x and self.min_y <= point.y <= self.max_y
        )

    def expand(self, margin: float) -> "BoundingBox":
        """Return a new box expanded by *margin* on every side."""
        return BoundingBox(
            min_x=self.min_x - margin,
            min_y=self.min_y - margin,
            max_x=self.max_x + margin,
            max_y=self.max_y + margin,
        )

    def union(self, other: "BoundingBox") -> "BoundingBox":
        """Return the smallest box that contains both boxes."""
        return BoundingBox(
            min_x=min(self.min_x, other.min_x),
            min_y=min(self.min_y, other.min_y),
            max_x=max(self.max_x, other.max_x),
            max_y=max(self.max_y, other.max_y),
        )

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_center(
        cls,
        center: Coordinate2D,
        half_w: float,
        half_h: float,
    ) -> "BoundingBox":
        """Create a box from its centre and half-extents."""
        return cls(
            min_x=center.x - half_w,
            min_y=center.y - half_h,
            max_x=center.x + half_w,
            max_y=center.y + half_h,
        )

    @classmethod
    def from_point(cls, point: Coordinate2D) -> "BoundingBox":
        """Create a degenerate (zero-area) box at *point*.

        Useful when a point geometry is needed that still satisfies the
        Geometry protocol (``area == 0``, ``centroid == point``).
        """
        return cls(
            min_x=point.x,
            min_y=point.y,
            max_x=point.x,
            max_y=point.y,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> JsonMap:
        """Serialise to a plain dict.

        The ``"type"`` key equals ``"bounding_box"`` and allows
        :meth:`from_dict` to round-trip correctly.
        """
        return {
            "type": _BOUNDING_BOX_TYPE,
            "min_x": self.min_x,
            "min_y": self.min_y,
            "max_x": self.max_x,
            "max_y": self.max_y,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BoundingBox":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Raises:
            ValueError: If required keys are absent or the ``type``
                discriminator does not match.
        """
        if data.get("type") != _BOUNDING_BOX_TYPE:
            raise ValueError(
                f"Expected type '{_BOUNDING_BOX_TYPE}', got {data.get('type')!r}"
            )
        try:
            return cls(
                min_x=float(data["min_x"]),
                min_y=float(data["min_y"]),
                max_x=float(data["max_x"]),
                max_y=float(data["max_y"]),
            )
        except KeyError as exc:
            raise ValueError(
                f"BoundingBox.from_dict: missing required key {exc}"
            ) from exc


# Runtime check that BoundingBox satisfies the Geometry protocol.
# This assertion fires at import time and catches any protocol drift.
assert isinstance(
    BoundingBox(0, 0, 1, 1), Geometry
), "BoundingBox does not satisfy the Geometry protocol"
