"""Tests for ometeotl_core.model.spaces."""

import pytest

from ometeotl_core.model.spaces import (
    Space,
    SpaceObjectGraph,
    SpaceObjectMembership,
)


def test_space_instantiation():
    """Verify that a space instantiates correctly."""
    space = Space(id="space-1")

    assert space.id == "space-1"
    assert space.object_type == "space"
    assert space.kind == "abstract"
    assert space.tags == []
    assert isinstance(space.dimensions, dict)


def test_space_object_graph_membership():
    """Verify that a space and membership can be added to the graph."""
    graph = SpaceObjectGraph()
    space = Space(id="space-1")

    graph.add_space(space)

    membership = SpaceObjectMembership(
        object_id="actor-1",
        space_id="space-1",
        role="occupies",
    )

    graph.add_object_membership(membership)

    found_spaces = graph.spaces_where_object_exists("actor-1")
    assert len(found_spaces) == 1
    assert found_spaces[0].id == "space-1"


def test_space_object_graph_lists_unique_object_ids_per_space():
    """list_objects_in_space remains stable even when one object has many roles."""
    graph = SpaceObjectGraph()
    graph.add_space(Space(id="space-roles"))
    graph.add_object_membership(
        SpaceObjectMembership(
            object_id="actor-dup",
            space_id="space-roles",
            role="occupies",
        )
    )
    graph.add_object_membership(
        SpaceObjectMembership(
            object_id="actor-dup",
            space_id="space-roles",
            role="observes",
        )
    )

    assert graph.list_objects_in_space("space-roles") == [
        "actor-dup"
    ]


def test_space_from_dict_null_optional_maps_defaults_empty():
    """Space should accept null optional maps in from_dict."""
    space = Space.from_dict(
        {"id": "s-null", "attributes": None, "relations": None}
    )

    assert isinstance(space.attributes, dict)
    assert space.relations == {}


def test_space_object_graph_from_dict_null_collections_defaults_empty():
    """SpaceObjectGraph should treat null collections as empty."""
    graph = SpaceObjectGraph.from_dict(
        {"spaces": None, "object_memberships": None}
    )

    assert graph.spaces == {}
    assert graph.object_memberships == []


def test_space_object_membership_from_dict_null_required_raises():
    """Membership deserialization should reject null required IDs."""
    with pytest.raises(ValueError):
        SpaceObjectMembership.from_dict(
            {
                "object_id": None,
                "space_id": "s1",
                "role": "occupies",
            }
        )
