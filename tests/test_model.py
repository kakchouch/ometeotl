# test/test_model.py
# ============================================================
# Tests de base du noyau modèle Ometeotl / MASM
#
# Objectif :
# - vérifier que les imports du package fonctionnent ;
# - vérifier que les objets de base s'instancient correctement ;
# - vérifier quelques comportements minimaux cohérents avec la V1.
# ============================================================
"""
Basic tests for ometeotl/MASM/model.
Objectives:
- Verify that package imports work correctly
- Verify that base objects instantiate properly
- Verify basic behaviors consistent with V1
"""
import pytest

# Import des classes depuis la nouvelle architecture packagée.
# MODIFICATION : on importe maintenant depuis "masm.model..."
from masm.model.base import ModelObject
from masm.model.objects import GenericObject
from masm.model.actors import Actor
from masm.model.resources import Resource
from masm.model.spaces import Space, SpaceObjectGraph, SpaceObjectMembership
from masm.model.space_relations import SpaceRelation, SpaceRelationGraph


def test_model_object_instantiation():
    """
    Vérifie que l'objet de base du modèle s'instancie correctement.
    """
    obj = ModelObject(id="obj-1", object_type="generic")

    assert obj.id == "obj-1"
    assert obj.object_type == "generic"
    assert isinstance(obj.attributes, dict)
    assert isinstance(obj.relations, dict)
    assert isinstance(obj.state, dict)
    assert isinstance(obj.context, dict)
    assert isinstance(obj.provenance, dict)


def test_model_object_add_relation():
    """
    Vérifie qu'une relation simple peut être ajoutée sans doublon.
    """
    obj = ModelObject(id="obj-1", object_type="generic")

    obj.add_relation("linkedto", "obj-2")
    obj.add_relation("linkedto", "obj-2")  # doublon volontaire

    assert "linkedto" in obj.relations
    assert obj.relations["linkedto"] == ["obj-2"]


def test_generic_object_label_and_description():
    """
    Vérifie le comportement minimal de GenericObject.
    """
    obj = GenericObject(id="g-1", object_type="generic")

    obj.label = "Mon objet"
    obj.description = "Description de test"

    assert obj.label == "Mon objet"
    assert obj.description == "Description de test"


def test_actor_instantiation():
    """
    Vérifie qu'un acteur s'instancie et reçoit ses attributs par défaut.
    """
    actor = Actor(id="actor-1")

    assert actor.id == "actor-1"
    assert actor.object_type == "actor"
    assert actor.roles == []


def test_actor_add_role_and_tag():
    """
    Vérifie qu'on peut enrichir un acteur avec un rôle et un tag.
    """
    actor = Actor(id="actor-1")

    actor.add_role("leader")
    actor.add_tag("human")

    assert "leader" in actor.roles
    assert "human" in actor.tags


def test_resource_instantiation():
    """
    Vérifie qu'une ressource s'instancie avec ses attributs par défaut.
    """
    resource = Resource(id="res-1")

    assert resource.id == "res-1"
    assert resource.object_type == "resource"
    assert resource.resource_mode == "stock"


def test_space_instantiation():
    """
    Vérifie qu'un espace s'instancie correctement.
    """
    space = Space(id="space-1")

    assert space.id == "space-1"
    assert space.object_type == "space"
    assert space.kind == "abstract"
    assert space.tags == []
    assert isinstance(space.dimensions, dict)


def test_space_object_graph_membership():
    """
    Vérifie qu'on peut ajouter un espace à un graphe
    puis y déclarer une appartenance d'objet.
    """
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


def test_space_relation_graph_adjacency():
    """
    Vérifie qu'une relation spatiale symétrique de type adjacentto
    peut être enregistrée proprement.
    """
    graph = SpaceRelationGraph()

    relation = SpaceRelation(
        source_space_id="space-a",
        target_space_id="space-b",
        relation_type="adjacent_to",
    )

    graph.add_relation(relation)

    neighbors_a = graph.neighbors_of("space-a")
    neighbors_b = graph.neighbors_of("space-b")

    assert "space-b" in neighbors_a
    assert "space-a" in neighbors_b


def test_empty_relation_name_raises():
    """
    Vérifie qu'une relation sans nom est refusée.
    """
    obj = ModelObject(id="obj-1", object_type="generic")

    with pytest.raises(ValueError):
        obj.add_relation("", "obj-2")


def test_empty_target_id_raises():
    """
    Vérifie qu'une relation sans cible est refusée.
    """
    obj = ModelObject(id="obj-1", object_type="generic")

    with pytest.raises(ValueError):
        obj.add_relation("linkedto", "")