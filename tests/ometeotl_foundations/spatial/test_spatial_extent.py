"""Tests for SpatialExtent."""

import copy

import pytest

from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.coordinate_system import CARTESIAN_2D, WGS84
from ometeotl_foundations.spatial.spatial_extent import SpatialExtent

_BOX = BoundingBox(1, 2, 3, 4)


class TestConstruction:
    def test_basic(self):
        e = SpatialExtent(space_id="s1", geometry=_BOX)
        assert e.space_id == "s1"
        assert e.geometry is _BOX
        assert e.coordinate_system == CARTESIAN_2D

    def test_custom_crs(self):
        e = SpatialExtent(space_id="s1", geometry=_BOX, coordinate_system=WGS84)
        assert e.coordinate_system == WGS84

    def test_metadata_default_empty(self):
        assert SpatialExtent(space_id="s1", geometry=_BOX).metadata == {}

    def test_frozen(self):
        e = SpatialExtent(space_id="s1", geometry=_BOX)
        with pytest.raises((AttributeError, TypeError)):
            e.space_id = "mutated"  # type: ignore[misc]


class TestSerialisation:
    def test_to_dict_keys(self):
        e = SpatialExtent(space_id="actor_1", geometry=_BOX)
        d = e.to_dict()
        assert set(d.keys()) == {
            "space_id",
            "geometry",
            "coordinate_system",
            "metadata",
        }

    def test_round_trip(self):
        original = SpatialExtent(
            space_id="city",
            geometry=BoundingBox(10, 20, 30, 40),
            coordinate_system=WGS84,
            metadata={"role": "footprint"},
        )
        restored = SpatialExtent.from_dict(original.to_dict(), BoundingBox.from_dict)
        assert restored.space_id == "city"
        assert restored.geometry == BoundingBox(10, 20, 30, 40)
        assert restored.coordinate_system == WGS84
        assert restored.metadata == {"role": "footprint"}

    def test_from_dict_missing_space_id(self):
        with pytest.raises((KeyError, ValueError)):
            SpatialExtent.from_dict(
                {
                    "geometry": _BOX.to_dict(),
                    "coordinate_system": CARTESIAN_2D.to_dict(),
                    "metadata": {},
                },
                BoundingBox.from_dict,
            )


class TestDeepCopy:
    def test_deepcopy_produces_equal_value(self):
        e = SpatialExtent(
            space_id="ref",
            geometry=_BOX,
            metadata={"tag": "original"},
        )
        cloned = copy.deepcopy(e)
        assert cloned.space_id == e.space_id
        assert cloned.geometry == e.geometry
        assert cloned.metadata == e.metadata

    def test_deepcopy_metadata_isolated(self):
        e = SpatialExtent(
            space_id="ref",
            geometry=_BOX,
            metadata={"tag": "original"},
        )
        cloned = copy.deepcopy(e)
        cloned.metadata["tag"] = "mutated"
        assert e.metadata["tag"] == "original"
