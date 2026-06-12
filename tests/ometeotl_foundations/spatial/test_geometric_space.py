"""Tests for GeometricSpace."""

import pytest

from ometeotl_core.model.spaces import Space
from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.coordinate_system import CARTESIAN_2D, WGS84
from ometeotl_foundations.spatial.geometric_space import GeometricSpace


def _make_space(space_id: str = "s1", kind: str = "physical") -> Space:
    s = Space(id=space_id)
    s.kind = kind
    return s


def _make_abstract_space(space_id: str = "abstract_s") -> Space:
    s = Space(id=space_id)
    s.is_abstract = True
    return s


_BOX = BoundingBox(0, 0, 10, 10)


class TestConstruction:
    def test_basic(self):
        space = _make_space()
        gs = GeometricSpace(space=space, geometry=_BOX)
        assert gs.space is space
        assert gs.geometry is _BOX
        assert gs.coordinate_system == CARTESIAN_2D

    def test_custom_crs(self):
        gs = GeometricSpace(space=_make_space(), geometry=_BOX, coordinate_system=WGS84)
        assert gs.coordinate_system == WGS84

    def test_metadata_default_empty(self):
        gs = GeometricSpace(space=_make_space(), geometry=_BOX)
        assert gs.metadata == {}

    def test_metadata_stored(self):
        gs = GeometricSpace(
            space=_make_space(), geometry=_BOX, metadata={"source": "survey"}
        )
        assert gs.metadata["source"] == "survey"

    def test_frozen(self):
        gs = GeometricSpace(space=_make_space(), geometry=_BOX)
        with pytest.raises((AttributeError, TypeError)):
            gs.geometry = BoundingBox(1, 1, 2, 2)  # type: ignore[misc]


class TestProxyProperties:
    def test_id(self):
        gs = GeometricSpace(space=_make_space("city"), geometry=_BOX)
        assert gs.id == "city"

    def test_kind(self):
        gs = GeometricSpace(space=_make_space(kind="virtual"), geometry=_BOX)
        assert gs.kind == "virtual"

    def test_is_abstract_false(self):
        gs = GeometricSpace(space=_make_space(), geometry=_BOX)
        assert gs.is_abstract is False

    def test_is_abstract_true(self):
        gs = GeometricSpace(space=_make_abstract_space(), geometry=_BOX)
        assert gs.is_abstract is True

    def test_dimensions(self):
        space = _make_space()
        space.set_dimension("altitude", 300)
        gs = GeometricSpace(space=space, geometry=_BOX)
        assert gs.dimensions["altitude"] == 300


class TestSerialisation:
    def test_to_dict_keys(self):
        gs = GeometricSpace(space=_make_space("s1"), geometry=_BOX)
        d = gs.to_dict()
        assert set(d.keys()) == {"space", "geometry", "coordinate_system", "metadata"}

    def test_to_dict_geometry_type(self):
        gs = GeometricSpace(space=_make_space(), geometry=_BOX)
        assert gs.to_dict()["geometry"]["type"] == "bounding_box"

    def test_round_trip(self):
        original = GeometricSpace(
            space=_make_space("harbor"),
            geometry=BoundingBox(5, 5, 15, 15),
            coordinate_system=WGS84,
            metadata={"label": "harbor district"},
        )
        d = original.to_dict()
        restored = GeometricSpace.from_dict(d, BoundingBox.from_dict)
        assert restored.id == "harbor"
        assert restored.geometry == BoundingBox(5, 5, 15, 15)
        assert restored.coordinate_system == WGS84
        assert restored.metadata == {"label": "harbor district"}

    def test_metadata_isolation_after_from_dict(self):
        gs = GeometricSpace(space=_make_space(), geometry=_BOX, metadata={"k": "v"})
        d = gs.to_dict()
        restored = GeometricSpace.from_dict(d, BoundingBox.from_dict)
        # Modifying the dict should not affect restored
        d["metadata"]["k"] = "mutated"
        assert restored.metadata.get("k") == "v"
