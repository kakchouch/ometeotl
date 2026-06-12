"""Tests for BoundingBox — the pure-Python Geometry implementation."""

import math

import pytest

from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.coordinates import Coordinate2D

# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_valid(self):
        b = BoundingBox(0.0, 0.0, 1.0, 1.0)
        assert b.min_x == 0.0 and b.max_y == 1.0

    def test_degenerate_point(self):
        b = BoundingBox(5.0, 5.0, 5.0, 5.0)
        assert b.area == 0.0

    def test_invalid_min_x_gt_max_x(self):
        with pytest.raises(ValueError, match="min_x"):
            BoundingBox(2.0, 0.0, 1.0, 1.0)

    def test_invalid_min_y_gt_max_y(self):
        with pytest.raises(ValueError, match="min_y"):
            BoundingBox(0.0, 2.0, 1.0, 1.0)

    def test_frozen(self):
        b = BoundingBox(0.0, 0.0, 1.0, 1.0)
        with pytest.raises((AttributeError, TypeError)):
            b.min_x = 9.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Geometry protocol — properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_area(self):
        assert BoundingBox(0, 0, 3, 4).area == 12.0

    def test_area_degenerate(self):
        assert BoundingBox(1, 1, 1, 1).area == 0.0

    def test_centroid(self):
        c = BoundingBox(0, 0, 4, 2).centroid
        assert c == Coordinate2D(2.0, 1.0)

    def test_bounds_is_self(self):
        b = BoundingBox(0, 0, 1, 1)
        assert b.bounds is b


# ---------------------------------------------------------------------------
# contains
# ---------------------------------------------------------------------------


class TestContains:
    def test_inner_fully_inside(self):
        outer = BoundingBox(0, 0, 10, 10)
        inner = BoundingBox(2, 2, 8, 8)
        assert outer.contains(inner)
        assert not inner.contains(outer)

    def test_identical_boxes(self):
        b = BoundingBox(0, 0, 5, 5)
        assert b.contains(b)

    def test_edge_touching(self):
        outer = BoundingBox(0, 0, 10, 10)
        edge = BoundingBox(0, 0, 5, 10)
        assert outer.contains(edge)

    def test_disjoint(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(6, 6, 10, 10)
        assert not a.contains(b)

    def test_partial_overlap(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(3, 3, 8, 8)
        assert not a.contains(b)

    def test_degenerate_point_inside(self):
        outer = BoundingBox(0, 0, 10, 10)
        point = BoundingBox.from_point(Coordinate2D(5, 5))
        assert outer.contains(point)

    def test_degenerate_point_on_boundary(self):
        outer = BoundingBox(0, 0, 10, 10)
        point = BoundingBox.from_point(Coordinate2D(0, 0))
        assert outer.contains(point)


# ---------------------------------------------------------------------------
# intersects
# ---------------------------------------------------------------------------


class TestIntersects:
    def test_overlapping(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(3, 3, 8, 8)
        assert a.intersects(b)
        assert b.intersects(a)

    def test_touching_edge(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(5, 0, 10, 5)
        assert a.intersects(b)

    def test_disjoint(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(6, 0, 10, 5)
        assert not a.intersects(b)

    def test_contained(self):
        outer = BoundingBox(0, 0, 10, 10)
        inner = BoundingBox(2, 2, 8, 8)
        assert outer.intersects(inner)


# ---------------------------------------------------------------------------
# touches
# ---------------------------------------------------------------------------


class TestTouches:
    def test_edge_touching(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(5, 0, 10, 5)
        assert a.touches(b)
        assert b.touches(a)

    def test_corner_touching(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(5, 5, 10, 10)
        assert a.touches(b)

    def test_overlapping_not_touching(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(3, 3, 8, 8)
        assert not a.touches(b)

    def test_overlapping_sharing_boundary_not_touching(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(2, 2, 4, 5)
        assert not a.touches(b)

    def test_disjoint_not_touching(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(6, 0, 10, 5)
        assert not a.touches(b)

    def test_contained_sharing_edge_not_touching(self):
        # A box fully inside another is NOT touching, even when it shares an edge.
        outer = BoundingBox(0, 0, 10, 10)
        inner = BoundingBox(
            0, 0, 5, 10
        )  # contained; shares outer's left/top/bottom edge
        assert outer.contains(inner)
        assert not outer.touches(inner)
        assert not inner.touches(outer)


# ---------------------------------------------------------------------------
# distance
# ---------------------------------------------------------------------------


class TestDistance:
    def test_overlapping_is_zero(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(3, 3, 8, 8)
        assert a.distance(b) == 0.0

    def test_touching_is_zero(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(5, 0, 10, 5)
        assert a.distance(b) == 0.0

    def test_disjoint_x_axis(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(8, 0, 10, 5)
        assert a.distance(b) == pytest.approx(3.0)

    def test_disjoint_y_axis(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(0, 7, 5, 10)
        assert a.distance(b) == pytest.approx(2.0)

    def test_disjoint_diagonal(self):
        a = BoundingBox(0, 0, 3, 3)
        b = BoundingBox(6, 7, 10, 10)
        # dx=3, dy=4 → 5
        assert a.distance(b) == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Convenience methods
# ---------------------------------------------------------------------------


class TestConvenience:
    def test_contains_point_inside(self):
        b = BoundingBox(0, 0, 10, 10)
        assert b.contains_point(Coordinate2D(5, 5))

    def test_contains_point_on_boundary(self):
        b = BoundingBox(0, 0, 10, 10)
        assert b.contains_point(Coordinate2D(0, 0))
        assert b.contains_point(Coordinate2D(10, 10))

    def test_contains_point_outside(self):
        b = BoundingBox(0, 0, 10, 10)
        assert not b.contains_point(Coordinate2D(11, 5))

    def test_expand(self):
        b = BoundingBox(2, 2, 8, 8).expand(1)
        assert b == BoundingBox(1, 1, 9, 9)

    def test_union(self):
        a = BoundingBox(0, 0, 5, 5)
        b = BoundingBox(3, 3, 10, 10)
        u = a.union(b)
        assert u == BoundingBox(0, 0, 10, 10)

    def test_from_center(self):
        b = BoundingBox.from_center(Coordinate2D(5, 5), half_w=2, half_h=3)
        assert b == BoundingBox(3, 2, 7, 8)

    def test_from_point(self):
        p = Coordinate2D(4, 7)
        b = BoundingBox.from_point(p)
        assert b.min_x == b.max_x == 4
        assert b.min_y == b.max_y == 7
        assert b.area == 0.0
        assert b.centroid == p


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


class TestSerialisation:
    def test_to_dict(self):
        b = BoundingBox(1, 2, 3, 4)
        d = b.to_dict()
        assert d["type"] == "bounding_box"
        assert d["min_x"] == 1 and d["max_y"] == 4

    def test_from_dict_round_trip(self):
        b = BoundingBox(1.5, 2.5, 3.5, 4.5)
        assert BoundingBox.from_dict(b.to_dict()) == b

    def test_from_dict_wrong_type(self):
        with pytest.raises(ValueError, match="type"):
            BoundingBox.from_dict({"type": "polygon", "min_x": 0})

    def test_from_dict_missing_key(self):
        with pytest.raises(ValueError):
            BoundingBox.from_dict({"type": "bounding_box", "min_x": 0})
