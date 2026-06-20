"""Tests for spatial_bridge.build_proximity_network."""

import pytest

from ometeotl_core.model.spaces import Space
from ometeotl_foundations.networks.spatial_bridge import build_proximity_network
from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.geometric_space import GeometricSpace


def _space(id_):
    return Space(id=id_)


def _gs(id_, x0, y0, x1, y1):
    return GeometricSpace(space=_space(id_), geometry=BoundingBox(x0, y0, x1, y1))


class TestBuildProximityNetwork:
    def test_empty_input_yields_empty_network(self):
        net = build_proximity_network(
            [],
            network_space=_space("empty-net"),
            max_distance=1.0,
        )
        assert net.nodes() == []
        assert net.connection_count == 0

    def test_single_space_no_connections(self):
        net = build_proximity_network(
            [_gs("A", 0, 0, 1, 1)],
            network_space=_space("net"),
            max_distance=1.0,
        )
        assert net.nodes() == ["A"]
        assert net.connection_count == 0

    def test_close_spaces_connected(self):
        gs1 = _gs("A", 0, 0, 1, 1)
        gs2 = _gs("B", 2, 0, 3, 1)  # distance 1.0 from gs1
        net = build_proximity_network(
            [gs1, gs2],
            network_space=_space("net"),
            max_distance=2.0,
        )
        assert net.has_connection("A", "B")

    def test_distant_spaces_not_connected(self):
        gs1 = _gs("A", 0, 0, 1, 1)
        gs2 = _gs("B", 100, 0, 101, 1)
        net = build_proximity_network(
            [gs1, gs2],
            network_space=_space("net"),
            max_distance=5.0,
        )
        assert not net.has_connection("A", "B")

    def test_threshold_at_boundary(self):
        gs1 = _gs("A", 0, 0, 1, 1)
        gs2 = _gs("B", 2, 0, 3, 1)  # distance exactly 1.0
        net_includes = build_proximity_network(
            [gs1, gs2], network_space=_space("net"), max_distance=1.0
        )
        net_excludes = build_proximity_network(
            [gs1, gs2], network_space=_space("net"), max_distance=0.9
        )
        assert net_includes.has_connection("A", "B")
        assert not net_excludes.has_connection("A", "B")

    def test_result_relations_is_valid_space_relation_graph(self):
        from ometeotl_core.model.space_relations import SpaceRelationGraph

        net = build_proximity_network(
            [_gs("A", 0, 0, 1, 1), _gs("B", 2, 0, 3, 1)],
            network_space=_space("net"),
            max_distance=2.0,
        )
        assert isinstance(net.relations, SpaceRelationGraph)
        assert len(net.relations.relations) == 1
        assert net.relations.relations[0].relation_type == "adjacent_to"

    def test_all_nodes_registered(self):
        """Every input space appears as a node even if isolated."""
        gs1 = _gs("A", 0, 0, 1, 1)
        gs2 = _gs("B", 100, 0, 101, 1)
        net = build_proximity_network(
            [gs1, gs2],
            network_space=_space("net"),
            max_distance=0.0,
        )
        assert "A" in net.nodes()
        assert "B" in net.nodes()

    def test_weight_stored_as_metadata(self):
        gs1 = _gs("A", 0, 0, 1, 1)
        gs2 = _gs("B", 2, 0, 3, 1)  # distance 1.0
        net = build_proximity_network(
            [gs1, gs2],
            network_space=_space("net"),
            max_distance=2.0,
            weight_fn=lambda d: d * 2,
        )
        from ometeotl_core.model.space_relations import SpaceRelation

        rels = net.relations.relations_from("A", "adjacent_to")
        assert len(rels) == 1
        assert rels[0].metadata.get("weight") == pytest.approx(2.0)

    def test_custom_relation_type(self):
        gs1 = _gs("A", 0, 0, 1, 1)
        gs2 = _gs("B", 2, 0, 3, 1)
        net = build_proximity_network(
            [gs1, gs2],
            network_space=_space("net"),
            max_distance=2.0,
            relation_type="intersects_with",
        )
        assert net.relations.relations[0].relation_type == "intersects_with"

    def test_skip_abstract_excludes_abstract_spaces(self):
        gs_normal = _gs("A", 0, 0, 1, 1)
        abstract_sp = Space(id="abstract-zone", attributes={"is_abstract": True})
        gs_abstract = GeometricSpace(
            space=abstract_sp, geometry=BoundingBox(2, 0, 3, 1)
        )
        # Verify is_abstract
        assert gs_abstract.is_abstract

        net = build_proximity_network(
            [gs_normal, gs_abstract],
            network_space=_space("net"),
            max_distance=100.0,
            skip_abstract=True,
        )
        assert "abstract-zone" not in net.nodes()

    def test_result_network_space_id(self):
        net = build_proximity_network(
            [],
            network_space=_space("my-network"),
            max_distance=1.0,
        )
        assert net.id == "my-network"

    def test_negative_max_distance_raises(self):
        with pytest.raises(ValueError, match="max_distance"):
            build_proximity_network([], network_space=_space("net"), max_distance=-1.0)
