"""Tests for derive_space_relations."""

import pytest

from ometeotl_core.model.spaces import Space
from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.geometric_space import GeometricSpace
from ometeotl_foundations.spatial.relation_derivation import derive_space_relations


def _gs(space_id: str, box: BoundingBox, abstract: bool = False) -> GeometricSpace:
    s = Space(id=space_id)
    if abstract:
        s.is_abstract = True
    return GeometricSpace(space=s, geometry=box)


# ---------------------------------------------------------------------------
# Basic topology
# ---------------------------------------------------------------------------


class TestBasicTopology:
    def test_disjoint_no_relations(self):
        a = _gs("a", BoundingBox(0, 0, 5, 5))
        b = _gs("b", BoundingBox(10, 10, 20, 20))
        graph = derive_space_relations([a, b])
        assert graph.relations == []

    def test_containment_a_contains_b(self):
        outer = _gs("outer", BoundingBox(0, 0, 10, 10))
        inner = _gs("inner", BoundingBox(2, 2, 8, 8))
        graph = derive_space_relations([outer, inner])
        ids = [
            (r.source_space_id, r.target_space_id, r.relation_type)
            for r in graph.relations
        ]
        assert ("outer", "inner", "contains_space") in ids
        assert not any(r.relation_type == "intersects_with" for r in graph.relations)

    def test_containment_b_contains_a(self):
        outer = _gs("outer", BoundingBox(0, 0, 10, 10))
        inner = _gs("inner", BoundingBox(2, 2, 8, 8))
        # reversed input order
        graph = derive_space_relations([inner, outer])
        ids = [
            (r.source_space_id, r.target_space_id, r.relation_type)
            for r in graph.relations
        ]
        assert ("outer", "inner", "contains_space") in ids

    def test_intersection(self):
        a = _gs("a", BoundingBox(0, 0, 6, 6))
        b = _gs("b", BoundingBox(4, 4, 10, 10))
        graph = derive_space_relations([a, b])
        types = [r.relation_type for r in graph.relations]
        assert "intersects_with" in types
        assert "contains_space" not in types

    def test_adjacency_touching(self):
        a = _gs("a", BoundingBox(0, 0, 5, 5))
        b = _gs("b", BoundingBox(5, 0, 10, 5))
        graph = derive_space_relations([a, b], adjacency_tolerance=0.0)
        # touching distance == 0, intersects is True for touching boxes
        # → intersects_with takes priority over adjacent_to
        types = [r.relation_type for r in graph.relations]
        assert "intersects_with" in types

    def test_adjacency_with_gap(self):
        a = _gs("a", BoundingBox(0, 0, 5, 5))
        b = _gs("b", BoundingBox(6, 0, 10, 5))  # gap of 1
        graph = derive_space_relations([a, b], adjacency_tolerance=1.0)
        types = [r.relation_type for r in graph.relations]
        assert "adjacent_to" in types

    def test_adjacency_gap_too_large(self):
        a = _gs("a", BoundingBox(0, 0, 5, 5))
        b = _gs("b", BoundingBox(8, 0, 12, 5))  # gap of 3
        graph = derive_space_relations([a, b], adjacency_tolerance=1.0)
        assert graph.relations == []


# ---------------------------------------------------------------------------
# skip_abstract
# ---------------------------------------------------------------------------


class TestSkipAbstract:
    def test_abstract_space_excluded_by_default(self):
        real = _gs("real", BoundingBox(0, 0, 10, 10))
        abstract = _gs("abstract", BoundingBox(2, 2, 8, 8), abstract=True)
        graph = derive_space_relations([real, abstract])
        space_ids = {r.source_space_id for r in graph.relations} | {
            r.target_space_id for r in graph.relations
        }
        assert "abstract" not in space_ids

    def test_abstract_included_when_skip_false(self):
        real = _gs("real", BoundingBox(0, 0, 10, 10))
        abstract = _gs("abstract", BoundingBox(2, 2, 8, 8), abstract=True)
        graph = derive_space_relations([real, abstract], skip_abstract=False)
        space_ids = {r.source_space_id for r in graph.relations} | {
            r.target_space_id for r in graph.relations
        }
        assert "abstract" in space_ids


# ---------------------------------------------------------------------------
# Derive flags
# ---------------------------------------------------------------------------


class TestDeriveFlags:
    def test_derive_containment_false_suppresses_containment(self):
        outer = _gs("outer", BoundingBox(0, 0, 10, 10))
        inner = _gs("inner", BoundingBox(2, 2, 8, 8))
        graph = derive_space_relations([outer, inner], derive_containment=False)
        types = [r.relation_type for r in graph.relations]
        assert "contains_space" not in types
        # They still intersect (inner box is inside outer)
        assert "intersects_with" in types

    def test_derive_intersection_false_suppresses_intersection(self):
        a = _gs("a", BoundingBox(0, 0, 6, 6))
        b = _gs("b", BoundingBox(4, 4, 10, 10))
        graph = derive_space_relations([a, b], derive_intersection=False)
        types = [r.relation_type for r in graph.relations]
        assert "intersects_with" not in types

    def test_derive_adjacency_false_suppresses_adjacency(self):
        a = _gs("a", BoundingBox(0, 0, 5, 5))
        b = _gs("b", BoundingBox(6, 0, 10, 5))
        graph = derive_space_relations(
            [a, b], adjacency_tolerance=2.0, derive_adjacency=False
        )
        assert graph.relations == []


# ---------------------------------------------------------------------------
# Core constraints enforced
# ---------------------------------------------------------------------------


class TestCoreConstraints:
    def test_antisymmetry_containment(self):
        """If A contains B, B cannot also contain A — core raises ValueError."""
        outer = _gs("outer", BoundingBox(0, 0, 10, 10))
        inner = _gs("inner", BoundingBox(2, 2, 8, 8))
        # derive_space_relations should produce exactly one direction
        graph = derive_space_relations([outer, inner])
        contains = [r for r in graph.relations if r.relation_type == "contains_space"]
        assert len(contains) == 1
        assert contains[0].source_space_id == "outer"
        assert contains[0].target_space_id == "inner"

    def test_empty_input(self):
        graph = derive_space_relations([])
        assert graph.relations == []

    def test_single_space_no_self_loop(self):
        gs = _gs("only", BoundingBox(0, 0, 5, 5))
        graph = derive_space_relations([gs])
        assert graph.relations == []


# ---------------------------------------------------------------------------
# Mixed 4-box scenario
# ---------------------------------------------------------------------------


class TestFourBoxScenario:
    def setup_method(self):
        """
        Layout:
          country  (0,0,100,100) — large outer box
          city     (10,10,40,40) — fully inside country
          harbor   (30,30,60,60) — overlaps city, inside country
          island   (200,200,300,300) — completely separate
        """
        self.country = _gs("country", BoundingBox(0, 0, 100, 100))
        self.city = _gs("city", BoundingBox(10, 10, 40, 40))
        self.harbor = _gs("harbor", BoundingBox(30, 30, 60, 60))
        self.island = _gs("island", BoundingBox(200, 200, 300, 300))
        self.spaces = [self.country, self.city, self.harbor, self.island]

    def test_country_contains_city(self):
        graph = derive_space_relations(self.spaces)
        ids = {
            (r.source_space_id, r.target_space_id): r.relation_type
            for r in graph.relations
        }
        assert ids.get(("country", "city")) == "contains_space"

    def test_country_contains_harbor(self):
        graph = derive_space_relations(self.spaces)
        ids = {
            (r.source_space_id, r.target_space_id): r.relation_type
            for r in graph.relations
        }
        assert ids.get(("country", "harbor")) == "contains_space"

    def test_city_and_harbor_intersect(self):
        graph = derive_space_relations(self.spaces)
        types = {
            frozenset([r.source_space_id, r.target_space_id]): r.relation_type
            for r in graph.relations
        }
        assert types.get(frozenset(["city", "harbor"])) == "intersects_with"

    def test_island_no_relation(self):
        graph = derive_space_relations(self.spaces)
        space_ids = {r.source_space_id for r in graph.relations} | {
            r.target_space_id for r in graph.relations
        }
        assert "island" not in space_ids
