"""Tests for GraphKind, GraphSpec, and predefined singletons."""

import pytest

from ometeotl_foundations.networks.graph_kind import (
    DIRECTED_SIMPLE,
    DIRECTED_WEIGHTED,
    UNDIRECTED_SIMPLE,
    UNDIRECTED_WEIGHTED,
    GraphKind,
    GraphSpec,
)


class TestGraphKind:
    def test_values(self):
        assert GraphKind.UNDIRECTED.value == "undirected"
        assert GraphKind.DIRECTED.value == "directed"
        assert GraphKind.WEIGHTED_UNDIRECTED.value == "weighted_undirected"
        assert GraphKind.WEIGHTED_DIRECTED.value == "weighted_directed"
        assert GraphKind.MULTIGRAPH.value == "multigraph"
        assert GraphKind.CUSTOM.value == "custom"

    def test_str_mixin(self):
        assert GraphKind.UNDIRECTED == "undirected"
        assert GraphKind.DIRECTED != "undirected"

    def test_all_members(self):
        kinds = {k.value for k in GraphKind}
        assert "undirected" in kinds
        assert "directed" in kinds


class TestGraphSpec:
    def test_construction_defaults(self):
        spec = GraphSpec(name="my_graph", kind=GraphKind.UNDIRECTED)
        assert spec.name == "my_graph"
        assert spec.kind == GraphKind.UNDIRECTED
        assert spec.allows_self_loops is False

    def test_construction_with_self_loops(self):
        spec = GraphSpec(name="loopy", kind=GraphKind.DIRECTED, allows_self_loops=True)
        assert spec.allows_self_loops is True

    def test_frozen(self):
        spec = GraphSpec(name="s", kind=GraphKind.UNDIRECTED)
        with pytest.raises(Exception):
            spec.name = "other"  # type: ignore[misc]

    def test_round_trip(self):
        spec = GraphSpec(
            name="directed_weighted",
            kind=GraphKind.WEIGHTED_DIRECTED,
            allows_self_loops=True,
        )
        d = spec.to_dict()
        assert d["name"] == "directed_weighted"
        assert d["kind"] == "weighted_directed"
        assert d["allows_self_loops"] is True
        restored = GraphSpec.from_dict(d)
        assert restored == spec

    def test_from_dict_missing_name_raises(self):
        with pytest.raises(ValueError, match="missing required key"):
            GraphSpec.from_dict({"kind": "undirected"})

    def test_from_dict_invalid_kind_raises(self):
        with pytest.raises(ValueError, match="invalid 'kind'"):
            GraphSpec.from_dict({"name": "x", "kind": "hexagonal"})

    def test_to_dict_includes_all_fields(self):
        spec = UNDIRECTED_SIMPLE
        d = spec.to_dict()
        assert "name" in d and "kind" in d and "allows_self_loops" in d


class TestPredefinedSingletons:
    def test_undirected_simple(self):
        assert UNDIRECTED_SIMPLE.kind == GraphKind.UNDIRECTED
        assert UNDIRECTED_SIMPLE.allows_self_loops is False

    def test_directed_simple(self):
        assert DIRECTED_SIMPLE.kind == GraphKind.DIRECTED

    def test_undirected_weighted(self):
        assert UNDIRECTED_WEIGHTED.kind == GraphKind.WEIGHTED_UNDIRECTED

    def test_directed_weighted(self):
        assert DIRECTED_WEIGHTED.kind == GraphKind.WEIGHTED_DIRECTED

    def test_singletons_are_distinct(self):
        specs = {
            UNDIRECTED_SIMPLE,
            DIRECTED_SIMPLE,
            UNDIRECTED_WEIGHTED,
            DIRECTED_WEIGHTED,
        }
        assert len(specs) == 4

    def test_singletons_round_trip(self):
        for singleton in (
            UNDIRECTED_SIMPLE,
            DIRECTED_SIMPLE,
            UNDIRECTED_WEIGHTED,
            DIRECTED_WEIGHTED,
        ):
            assert GraphSpec.from_dict(singleton.to_dict()) == singleton
