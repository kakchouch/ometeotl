"""Tests for ometeotl_core.model.base."""

import pytest

from ometeotl_core.model.base import (
    ModelObject,
    _dict_from_data,
    _str_from_data,
)


def test_model_object_instantiation():
    """Verify that the base model object instantiates correctly."""
    obj = ModelObject(id="obj-1", object_type="generic")

    assert obj.id == "obj-1"
    assert obj.object_type == "generic"
    assert isinstance(obj.attributes, dict)
    assert isinstance(obj.relations, dict)
    assert isinstance(obj.state, dict)
    assert isinstance(obj.context, dict)
    assert isinstance(obj.provenance, dict)


def test_model_object_add_relation():
    """Verify that a simple relation can be added without duplicates."""
    obj = ModelObject(id="obj-1", object_type="generic")

    obj.add_relation("linkedto", "obj-2")
    obj.add_relation("linkedto", "obj-2")

    assert "linkedto" in obj.relations
    assert obj.relations["linkedto"] == ["obj-2"]


def test_empty_relation_name_raises():
    """Verify that a relation without a name is rejected."""
    obj = ModelObject(id="obj-1", object_type="generic")

    with pytest.raises(ValueError):
        obj.add_relation("", "obj-2")


def test_empty_target_id_raises():
    """Verify that a relation without a target is rejected."""
    obj = ModelObject(id="obj-1", object_type="generic")

    with pytest.raises(ValueError):
        obj.add_relation("linkedto", "")


def test_model_object_from_dict_null_optional_maps_defaults_empty():
    """ModelObject.from_dict should treat null optional maps as empty dicts."""
    obj = ModelObject.from_dict(
        {
            "id": "obj-null-1",
            "object_type": "generic",
            "attributes": None,
            "relations": None,
            "state": None,
            "context": None,
            "provenance": None,
        }
    )
    assert obj.attributes == {}
    assert obj.relations == {}
    assert obj.state == {}
    assert obj.context == {}
    assert obj.provenance == {}


def test_model_object_from_dict_null_required_raises():
    """ModelObject.from_dict should reject null required identity fields."""
    with pytest.raises(ValueError):
        ModelObject.from_dict({"id": None, "object_type": "generic"})
    with pytest.raises(ValueError):
        ModelObject.from_dict({"id": "obj-1", "object_type": None})


def test_model_object_from_dict_rejects_unsupported_schema_version():
    """Schema version mismatches must be rejected (F-8)."""
    with pytest.raises(ValueError):
        ModelObject.from_dict(
            {
                "id": "obj-schema-1",
                "object_type": "generic",
                "schema_version": "2.0",
            }
        )


def test_str_from_data_empty_string_uses_default() -> None:
    """_str_from_data should treat empty strings like missing values."""
    payload = {"status": ""}
    assert _str_from_data(payload, "status", "active") == "active"


def test_str_from_data_zero_is_preserved() -> None:
    """_str_from_data should preserve non-empty falsy values by coercion."""
    payload = {"priority": 0}
    assert _str_from_data(payload, "priority", "1") == "0"


def test_dict_from_data_returns_copied_default_mapping() -> None:
    """_dict_from_data should return a copy of default mapping, not alias it."""
    default_map = {"k": "v"}
    extracted = _dict_from_data({}, "metadata", default_map)
    extracted["k"] = "changed"
    assert default_map == {"k": "v"}
    assert extracted == {"k": "changed"}


def test_dict_from_data_invalid_value_falls_back_to_default_copy() -> None:
    """_dict_from_data should use default mapping for non-mapping input."""
    default_map = {"safe": True}
    extracted = _dict_from_data({"metadata": 42}, "metadata", default_map)
    assert extracted == {"safe": True}
    assert extracted is not default_map
