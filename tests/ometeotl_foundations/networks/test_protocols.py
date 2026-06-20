"""Tests proving Graph Protocol conformance for all implementations."""

import pytest

from ometeotl_core.model.space_relations import SpaceRelationGraph
from ometeotl_foundations.networks.adjacency_graph import AdjacencyGraph
from ometeotl_foundations.networks.graph import Graph
from ometeotl_foundations.networks.relation_graph_adapter import (
    SpaceRelationGraphAdapter,
)


class TestGraphProtocolConformance:
    def test_adjacency_graph_satisfies_graph_protocol(self):
        assert isinstance(AdjacencyGraph(), Graph)

    def test_adjacency_graph_directed_satisfies_graph_protocol(self):
        assert isinstance(AdjacencyGraph.create(directed=True), Graph)

    def test_relation_graph_adapter_satisfies_graph_protocol(self):
        rg = SpaceRelationGraph()
        adapter = SpaceRelationGraphAdapter(rg)
        assert isinstance(adapter, Graph)

    def test_non_conforming_object_fails_protocol_check(self):
        class NotAGraph:
            pass

        assert not isinstance(NotAGraph(), Graph)

    def test_partial_conformance_fails(self):
        class PartialGraph:
            @property
            def is_directed(self) -> bool:
                return False

            @property
            def node_count(self) -> int:
                return 0

        assert not isinstance(PartialGraph(), Graph)

    def test_protocol_all_methods_present(self):
        required = {
            "is_directed",
            "node_count",
            "edge_count",
            "nodes",
            "edges",
            "has_node",
            "has_edge",
            "neighbors",
            "degree",
            "to_dict",
        }
        for attr in required:
            assert hasattr(AdjacencyGraph(), attr), f"Missing: {attr}"
