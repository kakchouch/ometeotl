"""Tests for CoordinateSystem and CoordinateKind."""

import pytest

from ometeotl_foundations.spatial.coordinate_system import (
    CARTESIAN_2D,
    CARTESIAN_3D,
    GRID,
    WGS84,
    CoordinateKind,
    CoordinateSystem,
)


class TestCoordinateKind:
    def test_string_values(self):
        assert CoordinateKind.CARTESIAN == "cartesian"
        assert CoordinateKind.GEOGRAPHIC == "geographic"
        assert CoordinateKind.GRID == "grid"
        assert CoordinateKind.CUSTOM == "custom"

    def test_json_serialisable_as_string(self):
        import json

        data = {"kind": CoordinateKind.CARTESIAN}
        dumped = json.dumps(data)
        assert '"cartesian"' in dumped


class TestCoordinateSystemSingletons:
    def test_cartesian_2d(self):
        assert CARTESIAN_2D.name == "cartesian_2d"
        assert CARTESIAN_2D.kind == CoordinateKind.CARTESIAN
        assert CARTESIAN_2D.unit == "meter"
        assert CARTESIAN_2D.srid is None

    def test_wgs84(self):
        assert WGS84.name == "wgs84"
        assert WGS84.kind == CoordinateKind.GEOGRAPHIC
        assert WGS84.unit == "degree"
        assert WGS84.srid == 4326

    def test_grid(self):
        assert GRID.kind == CoordinateKind.GRID
        assert GRID.unit == "cell"

    def test_cartesian_3d(self):
        assert CARTESIAN_3D.name == "cartesian_3d"


class TestCoordinateSystemSerialisation:
    def test_to_dict_without_srid(self):
        d = CARTESIAN_2D.to_dict()
        assert d["name"] == "cartesian_2d"
        assert d["kind"] == "cartesian"
        assert d["unit"] == "meter"
        assert "srid" not in d

    def test_to_dict_with_srid(self):
        d = WGS84.to_dict()
        assert d["srid"] == 4326

    def test_round_trip_without_srid(self):
        cs = CoordinateSystem.from_dict(CARTESIAN_2D.to_dict())
        assert cs == CARTESIAN_2D

    def test_round_trip_with_srid(self):
        cs = CoordinateSystem.from_dict(WGS84.to_dict())
        assert cs == WGS84

    def test_round_trip_custom(self):
        original = CoordinateSystem(
            name="my_crs", kind=CoordinateKind.CUSTOM, unit="km", srid=9999
        )
        cs = CoordinateSystem.from_dict(original.to_dict())
        assert cs == original

    def test_from_dict_missing_name(self):
        with pytest.raises(ValueError, match="name"):
            CoordinateSystem.from_dict({"kind": "cartesian", "unit": "meter"})

    def test_from_dict_invalid_kind(self):
        with pytest.raises(ValueError, match="kind"):
            CoordinateSystem.from_dict(
                {"name": "x", "kind": "invalid_kind", "unit": "m"}
            )
