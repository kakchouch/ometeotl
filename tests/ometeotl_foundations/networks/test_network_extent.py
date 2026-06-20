"""Tests for NetworkExtent."""

import pytest

from ometeotl_foundations.networks.network_extent import NetworkExtent


class TestNetworkExtent:
    def test_construction(self):
        ext = NetworkExtent(network_id="net-1", node_id="district-A")
        assert ext.network_id == "net-1"
        assert ext.node_id == "district-A"
        assert ext.metadata == {}

    def test_construction_with_metadata(self):
        ext = NetworkExtent(
            network_id="net-1",
            node_id="node-X",
            metadata={"role": "hub"},
        )
        assert ext.metadata == {"role": "hub"}

    def test_frozen(self):
        ext = NetworkExtent(network_id="net-1", node_id="A")
        with pytest.raises(Exception):
            ext.node_id = "B"  # type: ignore[misc]

    def test_round_trip(self):
        ext = NetworkExtent(
            network_id="net-2",
            node_id="node-Y",
            metadata={"weight": 3.0},
        )
        d = ext.to_dict()
        assert d["network_id"] == "net-2"
        assert d["node_id"] == "node-Y"
        restored = NetworkExtent.from_dict(d)
        assert restored.network_id == ext.network_id
        assert restored.node_id == ext.node_id
        assert restored.metadata == ext.metadata

    def test_round_trip_empty_metadata(self):
        ext = NetworkExtent(network_id="n", node_id="k")
        restored = NetworkExtent.from_dict(ext.to_dict())
        assert restored.metadata == {}

    def test_from_dict_missing_key_raises(self):
        with pytest.raises(KeyError):
            NetworkExtent.from_dict({"network_id": "net-1"})
