"""Tests for NetworkSpace[G] (generic frozen wrapper)."""

import pytest

from ometeotl_core.model.spaces import Space
from ometeotl_foundations.networks.adjacency_graph import AdjacencyGraph
from ometeotl_foundations.networks.graph_kind import DIRECTED_SIMPLE, UNDIRECTED_SIMPLE
from ometeotl_foundations.networks.network_space import NetworkSpace


def _space(id_="s-1"):
    return Space(id=id_)


def _graph_with_edges():
    g = AdjacencyGraph()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    return g


class TestNetworkSpaceConstruction:
    def test_basic_construction(self):
        ns = NetworkSpace(space=_space(), graph=AdjacencyGraph())
        assert ns.id == "s-1"
        assert ns.graph_spec == UNDIRECTED_SIMPLE

    def test_proxy_properties(self):
        sp = _space("net-2")
        ns = NetworkSpace(space=sp, graph=AdjacencyGraph())
        assert ns.id == sp.id
        assert ns.kind == sp.kind
        assert ns.is_abstract == sp.is_abstract
        assert ns.dimensions == sp.dimensions

    def test_metadata_defaults_empty(self):
        ns = NetworkSpace(space=_space(), graph=AdjacencyGraph())
        assert ns.metadata == {}

    def test_custom_graph_spec(self):
        ns = NetworkSpace(
            space=_space(), graph=AdjacencyGraph(), graph_spec=DIRECTED_SIMPLE
        )
        assert ns.graph_spec == DIRECTED_SIMPLE


class TestNetworkSpaceFrozen:
    def test_frozen(self):
        ns = NetworkSpace(space=_space(), graph=AdjacencyGraph())
        with pytest.raises(Exception):
            ns.graph_spec = DIRECTED_SIMPLE  # type: ignore[misc]


class TestNetworkSpaceSerialization:
    def test_round_trip_with_adjacency_graph(self):
        ns = NetworkSpace(
            space=_space("net-rt"),
            graph=_graph_with_edges(),
            graph_spec=UNDIRECTED_SIMPLE,
            metadata={"label": "test"},
        )
        d = ns.to_dict()
        assert "space" in d and "graph" in d and "graph_spec" in d

        restored = NetworkSpace.from_dict(d, AdjacencyGraph.from_dict)
        assert restored.id == ns.id
        assert restored.graph_spec == ns.graph_spec
        assert restored.graph.nodes() == ns.graph.nodes()
        assert restored.graph.edges() == ns.graph.edges()
        assert restored.metadata == {"label": "test"}

    def test_to_dict_includes_type_discriminator_in_graph(self):
        ns = NetworkSpace(space=_space(), graph=AdjacencyGraph())
        d = ns.to_dict()
        assert d["graph"]["type"] == "adjacency_graph"

    def test_from_dict_wrong_graph_type_propagates_error(self):
        d = {
            "space": _space().to_dict(),
            "graph": {"type": "not_adjacency_graph"},
            "graph_spec": UNDIRECTED_SIMPLE.to_dict(),
        }
        with pytest.raises(ValueError):
            NetworkSpace.from_dict(d, AdjacencyGraph.from_dict)

    def test_from_dict_missing_space_raises_value_error(self):
        d = {
            "graph": AdjacencyGraph().to_dict(),
            "graph_spec": UNDIRECTED_SIMPLE.to_dict(),
        }
        with pytest.raises(ValueError, match="space"):
            NetworkSpace.from_dict(d, AdjacencyGraph.from_dict)

    def test_from_dict_missing_graph_raises_value_error(self):
        d = {
            "space": _space().to_dict(),
            "graph_spec": UNDIRECTED_SIMPLE.to_dict(),
        }
        with pytest.raises(ValueError, match="graph"):
            NetworkSpace.from_dict(d, AdjacencyGraph.from_dict)

    def test_from_dict_missing_graph_spec_raises_value_error(self):
        d = {
            "space": _space().to_dict(),
            "graph": AdjacencyGraph().to_dict(),
        }
        with pytest.raises(ValueError, match="graph_spec"):
            NetworkSpace.from_dict(d, AdjacencyGraph.from_dict)
