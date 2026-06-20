"""Tests for AdjacencyGraph."""

import pytest

from ometeotl_foundations.networks.adjacency_graph import AdjacencyGraph


class TestUndirectedGraph:
    def setup_method(self):
        self.g = AdjacencyGraph()

    def test_empty(self):
        assert self.g.node_count == 0
        assert self.g.edge_count == 0
        assert self.g.nodes() == []
        assert self.g.edges() == []
        assert not self.g.is_directed

    def test_add_node(self):
        self.g.add_node("A")
        assert self.g.has_node("A")
        assert self.g.node_count == 1

    def test_add_node_idempotent(self):
        self.g.add_node("A")
        self.g.add_node("A")
        assert self.g.node_count == 1

    def test_add_edge_auto_creates_nodes(self):
        self.g.add_edge("A", "B")
        assert self.g.has_node("A")
        assert self.g.has_node("B")

    def test_edge_count_undirected(self):
        self.g.add_edge("A", "B")
        self.g.add_edge("B", "C")
        assert self.g.edge_count == 2

    def test_edges_sorted(self):
        self.g.add_edge("B", "A")  # canonical: A < B
        self.g.add_edge("C", "B")
        assert self.g.edges() == [("A", "B"), ("B", "C")]

    def test_nodes_sorted(self):
        self.g.add_edge("Z", "A")
        self.g.add_node("M")
        assert self.g.nodes() == ["A", "M", "Z"]

    def test_has_edge_both_directions(self):
        self.g.add_edge("A", "B")
        assert self.g.has_edge("A", "B")
        assert self.g.has_edge("B", "A")  # undirected
        assert self.g.has_edge("B", "A")  # undirected

    def test_self_loop_undirected(self):
        self.g.add_edge("A", "A")
        assert self.g.edge_count == 1
        assert self.g.edges() == [("A", "A")]
        assert self.g.has_edge("A", "A")
        assert self.g.neighbors("A") == ["A"]
        self.g.add_edge("A", "B")
        self.g.add_edge("A", "C")
        assert self.g.neighbors("A") == ["B", "C"]
        assert self.g.neighbors("B") == ["A"]

    def test_degree_undirected(self):
        self.g.add_edge("A", "B")
        self.g.add_edge("A", "C")
        assert self.g.degree("A") == 2
        assert self.g.degree("B") == 1

    def test_remove_edge(self):
        self.g.add_edge("A", "B")
        self.g.remove_edge("A", "B")
        assert not self.g.has_edge("A", "B")
        assert self.g.edge_count == 0

    def test_remove_edge_noop_if_absent(self):
        self.g.add_edge("A", "B")
        self.g.remove_edge("X", "Y")  # no-op
        assert self.g.edge_count == 1

    def test_remove_node_clears_incident_edges(self):
        self.g.add_edge("A", "B")
        self.g.add_edge("A", "C")
        self.g.remove_node("A")
        assert not self.g.has_node("A")
        assert not self.g.has_edge("A", "B")
        assert not self.g.has_edge("A", "C")
        assert self.g.node_count == 2  # B and C remain

    def test_remove_node_noop_if_absent(self):
        self.g.remove_node("nonexistent")  # no error

    def test_edge_weight_default(self):
        self.g.add_edge("A", "B")
        assert self.g.get_edge_weight("A", "B") == 1.0
        assert self.g.get_edge_weight("B", "A") == 1.0  # both directions

    def test_edge_weight_custom(self):
        self.g.add_edge("A", "B", weight=3.5)
        assert self.g.get_edge_weight("A", "B") == 3.5

    def test_get_edge_weight_absent(self):
        assert self.g.get_edge_weight("A", "B") is None

    def test_node_metadata(self):
        self.g.add_node("A", metadata={"color": "red"})
        assert self.g.get_node_metadata("A") == {"color": "red"}

    def test_node_metadata_absent(self):
        self.g.add_node("A")
        assert self.g.get_node_metadata("A") == {}

    def test_round_trip(self):
        self.g.add_node("A", metadata={"x": 1})
        self.g.add_edge("A", "B", weight=2.0)
        self.g.add_edge("B", "C")
        d = self.g.to_dict()
        restored = AdjacencyGraph.from_dict(d)
        assert restored.nodes() == self.g.nodes()
        assert restored.edges() == self.g.edges()
        assert restored.get_edge_weight("A", "B") == 2.0
        assert not restored.is_directed

    def test_from_dict_wrong_type_raises(self):
        with pytest.raises(ValueError, match="adjacency_graph"):
            AdjacencyGraph.from_dict({"type": "other"})


class TestDirectedGraph:
    def setup_method(self):
        self.g = AdjacencyGraph.create(directed=True)

    def test_is_directed(self):
        assert self.g.is_directed

    def test_edge_direction(self):
        self.g.add_edge("A", "B")
        assert self.g.has_edge("A", "B")
        assert not self.g.has_edge("B", "A")

    def test_edges_sorted_directed(self):
        self.g.add_edge("B", "A")
        self.g.add_edge("A", "C")
        assert self.g.edges() == [("A", "C"), ("B", "A")]

    def test_edge_count_directed(self):
        self.g.add_edge("A", "B")
        self.g.add_edge("B", "A")
        assert self.g.edge_count == 2

    def test_neighbors_directed(self):
        self.g.add_edge("A", "B")
        self.g.add_edge("A", "C")
        self.g.add_edge("D", "A")
        assert self.g.neighbors("A") == ["B", "C"]  # out-only

    def test_degree_directed(self):
        self.g.add_edge("A", "B")
        self.g.add_edge("A", "C")
        assert self.g.degree("A") == 2  # out-degree

    def test_remove_edge_directed(self):
        self.g.add_edge("A", "B")
        self.g.add_edge("B", "A")
        self.g.remove_edge("A", "B")
        assert not self.g.has_edge("A", "B")
        assert self.g.has_edge("B", "A")  # other direction intact

    def test_round_trip_directed(self):
        self.g.add_edge("A", "B")
        self.g.add_edge("B", "A")
        d = self.g.to_dict()
        assert d["directed"] is True
        restored = AdjacencyGraph.from_dict(d)
        assert restored.is_directed
        assert restored.has_edge("A", "B")
        assert restored.has_edge("B", "A")
