"""Tests for NetworkMap."""

from ometeotl_foundations.networks.network_extent import NetworkExtent
from ometeotl_foundations.networks.network_map import NetworkMap


def _ext(network_id, node_id):
    return NetworkExtent(network_id=network_id, node_id=node_id)


class TestNetworkMapCRUD:
    def test_empty(self):
        nm = NetworkMap()
        assert nm.all_ids() == []

    def test_set_position(self):
        nm = NetworkMap()
        nm.set_position("actor-1", _ext("net-1", "node-A"))
        assert nm.get_position("actor-1") is not None

    def test_get_position_absent(self):
        nm = NetworkMap()
        assert nm.get_position("ghost") is None

    def test_remove_position(self):
        nm = NetworkMap()
        nm.set_position("actor-1", _ext("net-1", "node-A"))
        nm.remove_position("actor-1")
        assert nm.get_position("actor-1") is None

    def test_remove_position_noop_if_absent(self):
        nm = NetworkMap()
        nm.remove_position("nonexistent")  # no error

    def test_set_position_replaces(self):
        nm = NetworkMap()
        nm.set_position("actor-1", _ext("net-1", "node-A"))
        nm.set_position("actor-1", _ext("net-1", "node-B"))
        assert nm.get_position("actor-1").node_id == "node-B"  # type: ignore[union-attr]

    def test_all_ids_sorted(self):
        nm = NetworkMap()
        nm.set_position("Z", _ext("net-1", "n1"))
        nm.set_position("A", _ext("net-1", "n2"))
        nm.set_position("M", _ext("net-1", "n3"))
        assert nm.all_ids() == ["A", "M", "Z"]

    def test_as_dict(self):
        nm = NetworkMap()
        ext = _ext("net-1", "node-A")
        nm.set_position("actor-1", ext)
        d = nm.as_dict()
        assert "actor-1" in d
        assert d["actor-1"] is ext  # same object (shallow copy)


class TestNetworkMapQueries:
    def test_objects_at_node(self):
        nm = NetworkMap()
        nm.set_position("actor-1", _ext("net-1", "node-A"))
        nm.set_position("actor-2", _ext("net-1", "node-A"))
        nm.set_position("actor-3", _ext("net-1", "node-B"))
        result = nm.objects_at_node("net-1", "node-A")
        assert result == ["actor-1", "actor-2"]

    def test_objects_at_node_empty(self):
        nm = NetworkMap()
        assert nm.objects_at_node("net-1", "node-X") == []

    def test_objects_in_network(self):
        nm = NetworkMap()
        nm.set_position("actor-1", _ext("net-1", "node-A"))
        nm.set_position("actor-2", _ext("net-2", "node-B"))
        nm.set_position("actor-3", _ext("net-1", "node-C"))
        result = nm.objects_in_network("net-1")
        assert result == ["actor-1", "actor-3"]

    def test_objects_in_network_empty(self):
        nm = NetworkMap()
        assert nm.objects_in_network("net-99") == []

    def test_objects_at_node_sorted(self):
        nm = NetworkMap()
        nm.set_position("Z", _ext("net-1", "node-A"))
        nm.set_position("A", _ext("net-1", "node-A"))
        result = nm.objects_at_node("net-1", "node-A")
        assert result == ["A", "Z"]

    def test_objects_in_network_sorted(self):
        nm = NetworkMap()
        nm.set_position("Z", _ext("net-1", "node-A"))
        nm.set_position("A", _ext("net-1", "node-B"))
        result = nm.objects_in_network("net-1")
        assert result == ["A", "Z"]
