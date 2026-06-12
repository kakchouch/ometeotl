"""Tests for SpatialMap."""

from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.coordinate_system import CARTESIAN_2D
from ometeotl_foundations.spatial.coordinates import Coordinate2D
from ometeotl_foundations.spatial.spatial_extent import SpatialExtent
from ometeotl_foundations.spatial.spatial_map import SpatialMap


def _extent(min_x, min_y, max_x, max_y) -> SpatialExtent:
    return SpatialExtent(
        space_id="ref",
        geometry=BoundingBox(min_x, min_y, max_x, max_y),
    )


class TestCRUD:
    def test_set_and_get(self):
        m: SpatialMap = SpatialMap()
        e = _extent(0, 0, 5, 5)
        m.set_extent("a1", e)
        assert m.get_extent("a1") is e

    def test_get_missing_returns_none(self):
        m: SpatialMap = SpatialMap()
        assert m.get_extent("unknown") is None

    def test_remove(self):
        m: SpatialMap = SpatialMap()
        m.set_extent("a1", _extent(0, 0, 5, 5))
        m.remove_extent("a1")
        assert m.get_extent("a1") is None

    def test_remove_missing_is_noop(self):
        m: SpatialMap = SpatialMap()
        m.remove_extent("nonexistent")  # must not raise

    def test_overwrite(self):
        m: SpatialMap = SpatialMap()
        m.set_extent("a1", _extent(0, 0, 5, 5))
        new_e = _extent(1, 1, 4, 4)
        m.set_extent("a1", new_e)
        assert m.get_extent("a1") is new_e

    def test_all_ids_sorted(self):
        m: SpatialMap = SpatialMap()
        for oid in ["z", "a", "m"]:
            m.set_extent(oid, _extent(0, 0, 1, 1))
        assert m.all_ids() == ["a", "m", "z"]

    def test_as_dict_is_copy(self):
        m: SpatialMap = SpatialMap()
        m.set_extent("a1", _extent(0, 0, 1, 1))
        d = m.as_dict()
        d["injected"] = _extent(0, 0, 1, 1)  # type: ignore[assignment]
        assert m.get_extent("injected") is None


class TestSpatialQueries:
    def setup_method(self):
        self.m: SpatialMap = SpatialMap()
        self.m.set_extent("left", _extent(0, 0, 5, 5))
        self.m.set_extent("right", _extent(7, 0, 12, 5))
        self.m.set_extent("middle", _extent(3, 3, 8, 8))

    def test_ids_containing_point_inside(self):
        result = self.m.ids_containing_point(Coordinate2D(4, 4))
        # BoundingBox.contains uses AABB: both "left" (0-5) and "middle" (3-8) contain (4,4)
        assert "left" in result
        assert "middle" in result
        assert "right" not in result

    def test_ids_containing_point_outside_all(self):
        result = self.m.ids_containing_point(Coordinate2D(20, 20))
        assert result == []

    def test_ids_intersecting(self):
        query = BoundingBox(4, 4, 9, 9)
        result = self.m.ids_intersecting(query)
        assert "middle" in result
        assert "right" in result  # BoundingBox(7,0,12,5) intersects (4,4,9,9)
        assert "left" in result  # BoundingBox(0,0,5,5) intersects (4,4,9,9)

    def test_empty_map_returns_empty(self):
        m: SpatialMap = SpatialMap()
        assert m.ids_containing_point(Coordinate2D(0, 0)) == []
        assert m.ids_intersecting(BoundingBox(0, 0, 100, 100)) == []
