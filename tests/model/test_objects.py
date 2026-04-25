"""Tests for masm.model.objects."""

from masm.model.objects import GenericObject
from masm.model.spaces import Space, SpaceObjectGraph


def test_generic_object_label_and_description():
    """Verify the minimal behavior of GenericObject."""
    obj = GenericObject(id="g-1", object_type="generic")

    obj.label = "Mon objet"
    obj.description = "Description de test"

    assert obj.label == "Mon objet"
    assert obj.description == "Description de test"


def test_generic_object_space_membership_helper_updates_graph():
    """Generic objects share the canonical space membership helper."""
    graph = SpaceObjectGraph()
    graph.add_space(Space(id="space-generic"))
    obj = GenericObject(id="generic-1", object_type="generic")

    obj.add_space_membership(
        graph,
        "space-generic",
        role="observes",
        metadata={"priority": 1},
    )

    assert len(graph.object_memberships) == 1
    assert graph.object_memberships[0].metadata == {
        "priority": 1
    }

    obj.remove_space_membership(
        graph, "space-generic", role="observes"
    )
    assert graph.object_memberships == []
