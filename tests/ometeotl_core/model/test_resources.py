"""Tests for ometeotl_core.model.resources."""

from ometeotl_core.model.resources import Resource


def test_resource_instantiation():
    """Verify that a resource instantiates with default attributes."""
    resource = Resource(id="res-1")

    assert resource.id == "res-1"
    assert resource.object_type == "resource"
    assert resource.resource_mode == "stock"


def test_resource_from_dict_null_optional_maps_defaults_empty():
    """Resource should accept null optional maps in from_dict."""
    resource = Resource.from_dict(
        {"id": "r-null", "attributes": None, "relations": None}
    )

    assert isinstance(resource.attributes, dict)
    assert resource.relations == {}
