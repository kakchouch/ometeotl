"""Tests for ometeotl_core.model.space_relations."""

import pytest

from ometeotl_core.model.space_relations import (
    SpaceRelation,
    SpaceRelationGraph,
)


def test_space_relation_graph_adjacency():
    """Verify that a symmetric adjacency relation is properly recorded."""
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


def test_space_relation_graph_from_dict_null_collections_defaults_empty():
    """SpaceRelationGraph should treat null collections as empty."""
    graph = SpaceRelationGraph.from_dict({"relations": None})

    assert graph.relations == []


def test_space_relation_from_dict_null_required_raises():
    """Relation deserialization should reject null required IDs."""
    with pytest.raises(ValueError):
        SpaceRelation.from_dict(
            {
                "source_space_id": None,
                "target_space_id": "s2",
                "relation_type": "adjacent_to",
            }
        )
