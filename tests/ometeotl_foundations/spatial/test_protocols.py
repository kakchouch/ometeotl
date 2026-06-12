"""Tests for Protocol structural typing checks."""

from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.coordinates import Coordinate2D
from ometeotl_foundations.spatial.geometry import Geometry


class TestGeometryProtocol:
    def test_bounding_box_satisfies_geometry(self):
        b = BoundingBox(0, 0, 1, 1)
        assert isinstance(b, Geometry)

    def test_non_conforming_object_fails(self):
        class NotAGeometry:
            pass

        assert not isinstance(NotAGeometry(), Geometry)

    def test_partial_conformance_fails(self):
        # Has area and centroid but missing other methods
        class PartialGeometry:
            @property
            def area(self) -> float:
                return 0.0

            @property
            def centroid(self) -> Coordinate2D:
                return Coordinate2D(0.0, 0.0)

        assert not isinstance(PartialGeometry(), Geometry)

    def test_custom_test_double_satisfies_protocol(self):
        """A hand-written double implementing all protocol members passes."""

        class FakeGeometry:
            @property
            def area(self) -> float:
                return 1.0

            @property
            def centroid(self) -> Coordinate2D:
                return Coordinate2D(0.0, 0.0)

            @property
            def bounds(self) -> BoundingBox:
                return BoundingBox(0, 0, 1, 1)

            def contains(self, other: Geometry) -> bool:
                return False

            def intersects(self, other: Geometry) -> bool:
                return False

            def touches(self, other: Geometry) -> bool:
                return False

            def distance(self, other: Geometry) -> float:
                return 0.0

            def to_dict(self) -> dict:
                return {"type": "fake"}

        assert isinstance(FakeGeometry(), Geometry)
