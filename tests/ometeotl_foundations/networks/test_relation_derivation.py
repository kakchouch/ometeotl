"""Tests for derive_space_relations_from_network."""

import pytest

from ometeotl_core.model.spaces import Space
from ometeotl_foundations.networks.adjacency_graph import AdjacencyGraph
from ometeotl_foundations.networks.adjacency_network_space import AdjacencyNetworkSpace
from ometeotl_foundations.networks.network_space import NetworkSpace
from ometeotl_foundations.networks.relation_derivation import (
    derive_space_relations_from_network,
)


def _space(id_="s-1"):
    return Space(id=id_)


def _ns_from_edges(*edges, directed=False):
    """Build NetworkSpace[AdjacencyGraph] from (source, target) pairs."""
    g = AdjacencyGraph.create(directed=directed)
    for u, v in edges:
        g.add_edge(u, v)
    return NetworkSpace(space=_space(), graph=g)


class TestDerivation:
    def test_empty_graph_yields_empty_sgraph(self):
        ns = _ns_from_edges()
        sgraph = derive_space_relations_from_network(ns)
        assert sgraph.relations == []

    def test_single_edge(self):
        ns = _ns_from_edges(("A", "B"))
        sgraph = derive_space_relations_from_network(ns)
        assert len(sgraph.relations) == 1
        rel = sgraph.relations[0]
        assert rel.relation_type == "adjacent_to"
        assert set([rel.source_space_id, rel.target_space_id]) == {"A", "B"}

    def test_multiple_edges_deduplicated(self):
        ns = _ns_from_edges(("A", "B"), ("B", "C"))
        sgraph = derive_space_relations_from_network(ns)
        assert len(sgraph.relations) == 2

    def test_self_loops_skipped(self):
        g = AdjacencyGraph.create(directed=True)
        g.add_node("A")
        # Self-loops can't be stored in AdjacencyGraph for directed graphs,
        # but if the graph reports them we must skip.  Simulate via a custom
        # read-only adapter that includes a self-loop edge.
        from ometeotl_core.model.space_relations import SpaceRelationGraph
        from ometeotl_foundations.networks.relation_graph_adapter import (
            SpaceRelationGraphAdapter,
        )

        rg = SpaceRelationGraph()
        adapter = SpaceRelationGraphAdapter(rg)

        class SelfLoopGraph:
            is_directed = False
            node_count = 1
            edge_count = 1

            def nodes(self):
                return ["A"]

            def edges(self):
                return [("A", "A")]

            def has_node(self, n):
                return n == "A"

            def has_edge(self, u, v):
                return u == v == "A"

            def neighbors(self, n):
                return []

            def degree(self, n):
                return 0

            def to_dict(self):
                return {"type": "self_loop"}

        ns_self = NetworkSpace(space=_space(), graph=SelfLoopGraph())
        sgraph = derive_space_relations_from_network(ns_self)
        assert sgraph.relations == []

    def test_custom_edge_relation_type(self):
        ns = _ns_from_edges(("parent", "child"), directed=True)
        sgraph = derive_space_relations_from_network(
            ns, edge_relation_type="contains_space"
        )
        assert len(sgraph.relations) == 1
        assert sgraph.relations[0].relation_type == "contains_space"

    def test_unknown_relation_type_raises(self):
        ns = _ns_from_edges(("A", "B"))
        with pytest.raises(ValueError):
            derive_space_relations_from_network(ns, edge_relation_type="unknown_type")

    def test_abstract_space_skipped_when_flag_set(self):
        class AbstractNetworkSpace:
            is_abstract = True
            graph = _ns_from_edges(("A", "B")).graph

        sgraph = derive_space_relations_from_network(
            AbstractNetworkSpace(), skip_abstract=True
        )
        assert sgraph.relations == []

    def test_abstract_not_skipped_when_flag_false(self):
        class AbstractNetworkSpace:
            is_abstract = True
            graph = _ns_from_edges(("A", "B")).graph

        sgraph = derive_space_relations_from_network(
            AbstractNetworkSpace(), skip_abstract=False
        )
        assert len(sgraph.relations) == 1

    def test_via_adjacency_network_space_to_network_space(self):
        """AdjacencyNetworkSpace + to_network_space → derive works correctly."""
        net = AdjacencyNetworkSpace(space=_space("net"))
        net.add_connection("A", "B")
        net.add_connection("B", "C")
        ns = net.to_network_space("adjacent_to")
        sgraph = derive_space_relations_from_network(ns)
        assert len(sgraph.relations) == 2
        types = {r.relation_type for r in sgraph.relations}
        assert types == {"adjacent_to"}

    def test_derived_graph_consistent_with_direct_relations(self):
        """Derived SpaceRelationGraph contains the same pairs as net.relations."""
        net = AdjacencyNetworkSpace(space=_space("net"))
        net.add_connection("A", "B")
        net.add_connection("B", "C")
        derived = derive_space_relations_from_network(net.to_network_space())
        direct = net.relations
        direct_pairs = {
            (r.source_space_id, r.target_space_id)
            for r in direct.relations
            if r.relation_type == "adjacent_to"
        }
        derived_pairs = {
            (r.source_space_id, r.target_space_id) for r in derived.relations
        }
        assert direct_pairs == derived_pairs
