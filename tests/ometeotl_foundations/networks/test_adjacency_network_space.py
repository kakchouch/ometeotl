"""Tests for AdjacencyNetworkSpace."""

import pytest

from ometeotl_core.model.spaces import Space
from ometeotl_foundations.networks.adjacency_network_space import AdjacencyNetworkSpace
from ometeotl_foundations.networks.graph import Graph
from ometeotl_foundations.networks.graph_kind import UNDIRECTED_SIMPLE
from ometeotl_foundations.networks.network_space import NetworkSpace
from ometeotl_foundations.networks.relation_graph_adapter import (
    SpaceRelationGraphAdapter,
)


def _space(id_="net-1"):
    return Space(id=id_)


def _net():
    return AdjacencyNetworkSpace(space=_space())


class TestProxyProperties:
    def test_id(self):
        sp = Space(id="my-net")
        net = AdjacencyNetworkSpace(space=sp)
        assert net.id == "my-net"

    def test_kind(self):
        sp = _space()
        net = AdjacencyNetworkSpace(space=sp)
        assert net.kind == sp.kind

    def test_is_abstract(self):
        sp = _space()
        net = AdjacencyNetworkSpace(space=sp)
        assert net.is_abstract == sp.is_abstract

    def test_dimensions(self):
        sp = _space()
        net = AdjacencyNetworkSpace(space=sp)
        assert net.dimensions == sp.dimensions


class TestNodeRegistration:
    def test_add_node_idempotent(self):
        net = _net()
        net.add_node("A")
        net.add_node("A")
        assert net.nodes() == ["A"]

    def test_isolated_node_appears_in_nodes(self):
        net = _net()
        net.add_node("isolated")
        assert "isolated" in net.nodes()

    def test_remove_node_from_node_ids(self):
        net = _net()
        net.add_node("A")
        net.remove_node("A")
        assert "A" not in net.nodes()

    def test_remove_node_clears_all_relations(self):
        net = _net()
        net.add_connection("A", "B")
        net.add_connection("A", "C")
        net.remove_node("A")
        assert not net.has_connection("A", "B")
        assert not net.has_connection("A", "C")
        assert "A" not in net.nodes()

    def test_remove_node_noop_if_absent(self):
        net = _net()
        net.remove_node("nonexistent")  # no error

    def test_node_count(self):
        net = _net()
        net.add_node("A")
        net.add_connection("B", "C")
        assert net.node_count == 3


class TestConnectionMutation:
    def test_add_connection_populates_relations(self):
        net = _net()
        net.add_connection("A", "B")
        assert len(net.relations.relations) == 1
        assert net.relations.relations[0].relation_type == "adjacent_to"

    def test_add_connection_symmetric(self):
        net = _net()
        net.add_connection("A", "B")
        assert net.has_connection("A", "B")
        assert net.has_connection("B", "A")

    def test_add_connection_deduplication(self):
        net = _net()
        net.add_connection("A", "B")
        net.add_connection("B", "A")  # duplicate after canonicalization
        assert net.connection_count == 1

    def test_add_connection_antisymmetry_from_core(self):
        net = _net()
        net.add_connection("parent", "child", "contains_space")
        with pytest.raises(ValueError):
            net.add_connection("child", "parent", "contains_space")

    def test_add_connection_self_loop_rejected(self):
        net = _net()
        with pytest.raises(ValueError):
            net.add_connection("A", "A", "adjacent_to")

    def test_add_connection_unknown_type_raises(self):
        net = _net()
        with pytest.raises(ValueError):
            net.add_connection("A", "B", "custom_unknown_type")

    def test_add_connection_with_metadata(self):
        net = _net()
        net.add_connection("A", "B", metadata={"weight": 2.5})
        rel = net.relations.relations[0]
        assert rel.metadata.get("weight") == 2.5

    def test_remove_connection_noop_if_absent(self):
        net = _net()
        net.add_connection("A", "B")
        net.remove_connection("A", "C")  # no-op
        assert net.connection_count == 1

    def test_remove_connection(self):
        net = _net()
        net.add_connection("A", "B")
        net.remove_connection("A", "B")
        assert not net.has_connection("A", "B")

    def test_connection_count(self):
        net = _net()
        net.add_connection("A", "B")
        net.add_connection("B", "C")
        assert net.connection_count == 2


class TestQueryMethods:
    def test_nodes_union(self):
        net = _net()
        net.add_node("isolated")
        net.add_connection("A", "B")
        assert set(net.nodes()) == {"isolated", "A", "B"}

    def test_has_node_via_node_ids(self):
        net = _net()
        net.add_node("X")
        assert net.has_node("X")

    def test_has_node_via_relations(self):
        net = _net()
        net.add_connection("A", "B")
        assert net.has_node("A")
        assert net.has_node("B")

    def test_has_node_absent(self):
        net = _net()
        assert not net.has_node("unknown")

    def test_neighbors_adjacent_to(self):
        net = _net()
        net.add_connection("A", "B")
        net.add_connection("A", "C")
        assert net.neighbors("A") == ["B", "C"]
        assert net.neighbors("B") == ["A"]

    def test_neighbors_contains_space(self):
        net = _net()
        net.add_connection("parent", "child1", "contains_space")
        net.add_connection("parent", "child2", "contains_space")
        # directed: only out-neighbors
        assert net.neighbors("parent", "contains_space") == ["child1", "child2"]
        assert net.neighbors("child1", "contains_space") == []

    def test_connections_of(self):
        net = _net()
        net.add_connection("A", "B")
        net.add_connection("A", "C")
        rels = net.connections_of("A")
        assert len(rels) == 2

    def test_connections_of_filtered(self):
        net = _net()
        net.add_connection("A", "B", "adjacent_to")
        net.add_connection("parent", "A", "contains_space")
        adj_rels = net.connections_of("A", "adjacent_to")
        assert all(r.relation_type == "adjacent_to" for r in adj_rels)


class TestAsGraph:
    def test_as_graph_returns_adapter(self):
        net = _net()
        net.add_connection("A", "B")
        g = net.as_graph("adjacent_to")
        assert isinstance(g, SpaceRelationGraphAdapter)
        assert isinstance(g, Graph)

    def test_as_graph_is_undirected_for_adjacent_to(self):
        net = _net()
        g = net.as_graph("adjacent_to")
        assert not g.is_directed

    def test_as_graph_is_directed_for_contains_space(self):
        net = _net()
        g = net.as_graph("contains_space")
        assert g.is_directed

    def test_as_graph_includes_isolated_nodes(self):
        net = _net()
        net.add_node("isolated")
        g = net.as_graph("adjacent_to")
        assert "isolated" in g.nodes()

    def test_to_network_space_returns_network_space(self):
        net = _net()
        net.add_connection("A", "B")
        ns = net.to_network_space("adjacent_to")
        assert isinstance(ns, NetworkSpace)
        assert ns.id == net.id
        assert ("A", "B") in ns.graph.edges()


class TestRelationsProperty:
    def test_relations_is_live_object(self):
        net = _net()
        net.add_connection("A", "B")
        sgraph = net.relations
        assert len(sgraph.relations) == 1
        net.add_connection("B", "C")
        assert len(sgraph.relations) == 2  # live reference


class TestSerialization:
    def test_round_trip_empty(self):
        net = _net()
        d = net.to_dict()
        restored = AdjacencyNetworkSpace.from_dict(d)
        assert restored.id == net.id
        assert restored.nodes() == []

    def test_round_trip_with_nodes_and_connections(self):
        net = _net()
        net.add_node("isolated")
        net.add_connection("A", "B")
        net.add_connection("B", "C")
        d = net.to_dict()
        restored = AdjacencyNetworkSpace.from_dict(d)
        assert "isolated" in restored.nodes()
        assert restored.has_connection("A", "B")
        assert restored.has_connection("B", "C")
        assert not restored.has_connection("A", "C")

    def test_round_trip_preserves_graph_spec(self):
        from ometeotl_foundations.networks.graph_kind import DIRECTED_WEIGHTED

        net = AdjacencyNetworkSpace(space=_space(), graph_spec=DIRECTED_WEIGHTED)
        d = net.to_dict()
        restored = AdjacencyNetworkSpace.from_dict(d)
        assert restored.graph_spec == DIRECTED_WEIGHTED

    def test_round_trip_preserves_metadata(self):
        net = AdjacencyNetworkSpace(space=_space(), metadata={"label": "city-net"})
        d = net.to_dict()
        restored = AdjacencyNetworkSpace.from_dict(d)
        assert restored.metadata.get("label") == "city-net"

    def test_from_dict_missing_space_raises_value_error(self):
        with pytest.raises(ValueError, match="space"):
            AdjacencyNetworkSpace.from_dict({"graph_spec": UNDIRECTED_SIMPLE.to_dict()})

    def test_from_dict_missing_graph_spec_raises_value_error(self):
        with pytest.raises(ValueError, match="graph_spec"):
            AdjacencyNetworkSpace.from_dict({"space": _space().to_dict()})
