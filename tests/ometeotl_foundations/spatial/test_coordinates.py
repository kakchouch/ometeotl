"""Tests for coordinate value types."""

import pytest

from ometeotl_foundations.spatial.coordinates import (
    Coordinate2D,
    Coordinate3D,
    GeoCoordinate,
    GridCell,
)


class TestCoordinate2D:
    def test_fields(self):
        c = Coordinate2D(x=1.0, y=2.0)
        assert c.x == 1.0
        assert c.y == 2.0

    def test_frozen(self):
        c = Coordinate2D(x=0.0, y=0.0)
        with pytest.raises((AttributeError, TypeError)):
            c.x = 1.0  # type: ignore[misc]

    def test_equality(self):
        assert Coordinate2D(1.0, 2.0) == Coordinate2D(1.0, 2.0)
        assert Coordinate2D(1.0, 2.0) != Coordinate2D(1.0, 3.0)

    def test_hashable(self):
        s = {Coordinate2D(1.0, 2.0), Coordinate2D(1.0, 2.0)}
        assert len(s) == 1


class TestCoordinate3D:
    def test_fields(self):
        c = Coordinate3D(x=1.0, y=2.0, z=3.0)
        assert c.z == 3.0

    def test_frozen(self):
        c = Coordinate3D(0.0, 0.0, 0.0)
        with pytest.raises((AttributeError, TypeError)):
            c.z = 9.0  # type: ignore[misc]


class TestGeoCoordinate:
    def test_valid(self):
        g = GeoCoordinate(longitude=10.0, latitude=50.0)
        assert g.longitude == 10.0
        assert g.latitude == 50.0
        assert g.altitude == 0.0

    def test_altitude_default(self):
        assert GeoCoordinate(0.0, 0.0).altitude == 0.0

    def test_invalid_longitude_too_low(self):
        with pytest.raises(ValueError, match="longitude"):
            GeoCoordinate(longitude=-181.0, latitude=0.0)

    def test_invalid_longitude_too_high(self):
        with pytest.raises(ValueError, match="longitude"):
            GeoCoordinate(longitude=181.0, latitude=0.0)

    def test_invalid_latitude_too_low(self):
        with pytest.raises(ValueError, match="latitude"):
            GeoCoordinate(longitude=0.0, latitude=-91.0)

    def test_invalid_latitude_too_high(self):
        with pytest.raises(ValueError, match="latitude"):
            GeoCoordinate(longitude=0.0, latitude=91.0)

    def test_boundary_values(self):
        GeoCoordinate(longitude=-180.0, latitude=-90.0)
        GeoCoordinate(longitude=180.0, latitude=90.0)

    def test_frozen(self):
        g = GeoCoordinate(0.0, 0.0)
        with pytest.raises((AttributeError, TypeError)):
            g.longitude = 1.0  # type: ignore[misc]


class TestGridCell:
    def test_fields(self):
        c = GridCell(col=3, row=-2)
        assert c.col == 3
        assert c.row == -2
        assert c.layer == 0

    def test_negative_coordinates_are_valid(self):
        c = GridCell(col=-10, row=-20, layer=-1)
        assert c.col == -10

    def test_frozen(self):
        c = GridCell(0, 0)
        with pytest.raises((AttributeError, TypeError)):
            c.col = 1  # type: ignore[misc]
