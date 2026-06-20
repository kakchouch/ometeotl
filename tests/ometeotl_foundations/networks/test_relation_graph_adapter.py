"""Tests for SpaceRelationGraphAdapter."""

import pytest

from ometeotl_core.model.space_relations import SpaceRelation, SpaceRelationGraph
from ometeotl_foundations.networks.relation_graph_adapter import (
    SpaceRelationGraphAdapter,
)


def _make_rg(*pairs, relation_type="adjacent_to"):
    """Build a SpaceRelationGraph from (source, target) pairs."""
    rg = SpaceRelationGraph()
    for src, tgt in pairs:
        rg.add_relation(SpaceRelation(src, tgt, relation_type))
    return rg


class TestIsDirected:
    def test_adjacent_to_is_undirected(self):
        adapter = SpaceRelationGraphAdapter(
            SpaceRelationGraph(), _relation_type="adjacent_to"
        )
        assert not adapter.is_directed

    def test_intersects_with_is_undirected(self):
        adapter = SpaceRelationGraphAdapter(
            SpaceRelationGraph(), _relation_type="intersects_with"
        )
        assert not adapter.is_directed

    def test_contains_space_is_directed(self):
        adapter = SpaceRelationGraphAdapter(
            SpaceRelationGraph(), _relation_type="contains_space"
        )
        assert adapter.is_directed

    def test_unknown_type_defaults_to_directed(self):
        adapter = SpaceRelationGraphAdapter(
            SpaceRelationGraph(), _relation_type="custom_type_xyz"
        )
        assert adapter.is_directed


class TestNodes:
    def test_empty_graph_no_nodes(self):
        adapter = SpaceRelationGraphAdapter(SpaceRelationGraph())
        assert adapter.nodes() == []

    def test_nodes_from_relations(self):
        rg = _make_rg(("A", "B"), ("B", "C"))
        adapter = SpaceRelationGraphAdapter(rg)
        assert adapter.nodes() == ["A", "B", "C"]

    def test_isolated_nodes_from_node_ids(self):
        rg = _make_rg(("A", "B"))
        adapter = SpaceRelationGraphAdapter(rg, _node_ids=frozenset({"X"}))
        assert "X" in adapter.nodes()

    def test_nodes_sorted(self):
        rg = _make_rg(("Z", "A"), ("M", "A"))
        adapter = SpaceRelationGraphAdapter(rg)
        assert adapter.nodes() == sorted(adapter.nodes())

    def test_nodes_filtered_by_relation_type(self):
        rg = _make_rg(("A", "B"), relation_type="adjacent_to")
        rg.add_relation(SpaceRelation("C", "D", "intersects_with"))
        adapter = SpaceRelationGraphAdapter(rg, _relation_type="adjacent_to")
        assert "C" not in adapter.nodes()
        assert "D" not in adapter.nodes()


class TestEdges:
    def test_edges_symmetric_canonicalized(self):
        rg = _make_rg(("B", "A"))  # stored as (A, B) after canonicalization
        adapter = SpaceRelationGraphAdapter(rg)
        assert ("A", "B") in adapter.edges()

    def test_edges_filtered_by_relation_type(self):
        rg = _make_rg(("A", "B"), relation_type="adjacent_to")
        rg.add_relation(SpaceRelation("C", "D", "intersects_with"))
        adj_adapter = SpaceRelationGraphAdapter(rg, _relation_type="adjacent_to")
        int_adapter = SpaceRelationGraphAdapter(rg, _relation_type="intersects_with")
        assert ("A", "B") in adj_adapter.edges()
        assert ("C", "D") in int_adapter.edges()
        assert ("C", "D") not in adj_adapter.edges()

    def test_edges_empty(self):
        adapter = SpaceRelationGraphAdapter(SpaceRelationGraph())
        assert adapter.edges() == []


class TestHasEdge:
    def test_has_edge_o1_via_relation_keys(self):
        rg = _make_rg(("A", "B"))
        adapter = SpaceRelationGraphAdapter(rg)
        assert adapter.has_edge("A", "B")
        assert adapter.has_edge("B", "A")  # symmetric lookup

    def test_has_edge_absent(self):
        rg = _make_rg(("A", "B"))
        adapter = SpaceRelationGraphAdapter(rg)
        assert not adapter.has_edge("A", "C")

    def test_has_edge_directed_contains_space(self):
        rg = SpaceRelationGraph()
        rg.add_relation(SpaceRelation("parent", "child", "contains_space"))
        adapter = SpaceRelationGraphAdapter(rg, _relation_type="contains_space")
        assert adapter.has_edge("parent", "child")
        assert not adapter.has_edge("child", "parent")


class TestNeighbors:
    def test_neighbors_symmetric(self):
        rg = _make_rg(("A", "B"), ("A", "C"))
        adapter = SpaceRelationGraphAdapter(rg)
        assert adapter.neighbors("A") == ["B", "C"]
        assert adapter.neighbors("B") == ["A"]

    def test_neighbors_directed_out_only(self):
        rg = SpaceRelationGraph()
        rg.add_relation(SpaceRelation("parent", "child", "contains_space"))
        adapter = SpaceRelationGraphAdapter(rg, _relation_type="contains_space")
        assert adapter.neighbors("parent") == ["child"]
        assert adapter.neighbors("child") == []

    def test_degree_equals_neighbor_count(self):
        rg = _make_rg(("A", "B"), ("A", "C"))
        adapter = SpaceRelationGraphAdapter(rg)
        assert adapter.degree("A") == 2
        assert adapter.degree("B") == 1


class TestCounts:
    def test_node_count(self):
        rg = _make_rg(("A", "B"), ("B", "C"))
        adapter = SpaceRelationGraphAdapter(rg)
        assert adapter.node_count == 3

    def test_edge_count(self):
        rg = _make_rg(("A", "B"), ("B", "C"))
        adapter = SpaceRelationGraphAdapter(rg)
        assert adapter.edge_count == 2


class TestToDict:
    def test_to_dict_includes_type_discriminator(self):
        adapter = SpaceRelationGraphAdapter(SpaceRelationGraph())
        d = adapter.to_dict()
        assert d["type"] == "relation_graph_adapter"
        assert "relation_type" in d
        assert "is_directed" in d


class TestFromDict:
    def test_round_trip_empty(self):
        adapter = SpaceRelationGraphAdapter(SpaceRelationGraph())
        restored = SpaceRelationGraphAdapter.from_dict(adapter.to_dict())
        assert restored.edges() == []
        assert restored.nodes() == []

    def test_round_trip_with_edges(self):
        rg = _make_rg(("A", "B"), ("B", "C"))
        adapter = SpaceRelationGraphAdapter(rg)
        restored = SpaceRelationGraphAdapter.from_dict(adapter.to_dict())
        assert restored.edges() == adapter.edges()
        assert restored.nodes() == adapter.nodes()
        assert not restored.is_directed

    def test_round_trip_directed(self):
        rg = SpaceRelationGraph()
        rg.add_relation(SpaceRelation("parent", "child", "contains_space"))
        adapter = SpaceRelationGraphAdapter(rg, _relation_type="contains_space")
        restored = SpaceRelationGraphAdapter.from_dict(adapter.to_dict())
        assert restored.is_directed
        assert restored.has_edge("parent", "child")
        assert not restored.has_edge("child", "parent")

    def test_round_trip_preserves_node_ids(self):
        rg = _make_rg(("A", "B"))
        adapter = SpaceRelationGraphAdapter(rg, _node_ids=frozenset({"isolated"}))
        restored = SpaceRelationGraphAdapter.from_dict(adapter.to_dict())
        assert "isolated" in restored.nodes()

    def test_wrong_type_raises(self):
        with pytest.raises(ValueError, match="relation_graph_adapter"):
            SpaceRelationGraphAdapter.from_dict({"type": "other"})

    def test_missing_relation_type_raises(self):
        with pytest.raises(ValueError):
            SpaceRelationGraphAdapter.from_dict({"type": "relation_graph_adapter"})
