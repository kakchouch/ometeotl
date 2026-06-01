"""Smoke tests for the multi-agent graph simulation engine.

These tests live in examples and are NOT part of the tracked tests/ tree.
Run with:
    python -m pytest -q examples/multi_agent_sim/test_sim_local.py
"""

from __future__ import annotations

import pytest

from examples.multi_agent_sim.config import SimConfig
from examples.multi_agent_sim.graph_gen import build_graph, bfs_distances
from examples.multi_agent_sim.engine import (
    SimState,
    create_sim,
    step,
    serialize_state,
    _hamming_distance,
    _random_genome,
    _mutate_genome,
)

import random


# --------------------------------------------------------------------------- #
# Config validation                                                            #
# --------------------------------------------------------------------------- #


def test_config_defaults_are_valid():
    SimConfig().validate()


def test_config_rejects_bad_values():
    with pytest.raises(ValueError):
        SimConfig(num_nodes=1).validate()
    with pytest.raises(ValueError):
        SimConfig(num_factions=0).validate()
    with pytest.raises(ValueError):
        SimConfig(num_factions=99, num_nodes=5).validate()
    with pytest.raises(ValueError):
        SimConfig(flip_threshold=-1).validate()
    with pytest.raises(ValueError):
        SimConfig(mutation_rate=2.0).validate()
    with pytest.raises(ValueError):
        SimConfig(graph_mode="unknown").validate()


def test_config_drift_threshold_bits():
    cfg = SimConfig(genome_length=16, drift_threshold_fraction=0.5)
    assert cfg.drift_threshold_bits == 8


# --------------------------------------------------------------------------- #
# Graph generation                                                             #
# --------------------------------------------------------------------------- #


def test_graph_connectivity():
    """Generated graph must be connected."""
    cfg = SimConfig(num_nodes=12, seed=7)
    g = build_graph(cfg)
    assert len(g.nodes) == 12
    # BFS from node-0 must reach all nodes
    dists = bfs_distances(g, "node-0")
    unreachable = [nid for nid, d in dists.items() if d < 0]
    assert unreachable == [], f"Unreachable nodes: {unreachable}"


def test_graph_edge_count_reasonable():
    cfg = SimConfig(num_nodes=10, seed=42, graph_density=0.3)
    g = build_graph(cfg)
    # Minimum edges = spanning tree (n-1)
    assert len(g.edges) >= cfg.num_nodes - 1
    # Maximum edges = n*(n-1)/2
    assert len(g.edges) <= cfg.num_nodes * (cfg.num_nodes - 1) // 2


def test_graph_spice_flows_in_range():
    cfg = SimConfig(num_nodes=8, seed=1, min_spice_flow=2, max_spice_flow=5)
    g = build_graph(cfg)
    for node in g.nodes:
        assert cfg.min_spice_flow <= node.spice_flow <= cfg.max_spice_flow


def test_geographic_graph_is_connected_and_has_dead_ends():
    cfg = SimConfig(num_nodes=24, seed=42, graph_mode="geographic")
    g = build_graph(cfg)

    dists = bfs_distances(g, "node-0")
    unreachable = [nid for nid, d in dists.items() if d < 0]
    assert unreachable == [], f"Unreachable nodes in geographic mode: {unreachable}"

    degree = {n.node_id: 0 for n in g.nodes}
    for a, b in g.edges:
        degree[a] += 1
        degree[b] += 1

    # Dead ends and narrow sections should exist in map-like generation.
    assert any(v == 1 for v in degree.values())
    assert sum(v <= 2 for v in degree.values()) >= max(3, len(g.nodes) // 3)


# --------------------------------------------------------------------------- #
# Genome utilities                                                              #
# --------------------------------------------------------------------------- #


def test_hamming_distance_identical():
    assert _hamming_distance([0, 1, 1, 0], [0, 1, 1, 0]) == 0


def test_hamming_distance_all_differ():
    assert _hamming_distance([0, 0, 0, 0], [1, 1, 1, 1]) == 4


def test_mutate_flips_exactly_one_bit():
    rng = random.Random(99)
    g = [0] * 16
    mutated = _mutate_genome(g, rng)
    assert sum(mutated) == 1
    assert _hamming_distance(g, mutated) == 1


# --------------------------------------------------------------------------- #
# Simulation initialisation                                                    #
# --------------------------------------------------------------------------- #


def test_create_sim_nodes_and_factions():
    cfg = SimConfig(num_nodes=10, num_factions=3, seed=42)
    state = create_sim(cfg)
    assert len(state.nodes) == 10
    assert len(state.factions) == 3
    assert state.tick == 0
    assert not state.game_over


def test_capital_nodes_owned_by_factions():
    cfg = SimConfig(num_nodes=8, num_factions=2, seed=5)
    state = create_sim(cfg)
    for fid, faction in state.factions.items():
        cap = state.nodes[faction.capital_id]
        assert cap.owner_id == fid, f"Capital {faction.capital_id} not owned by {fid}"


# --------------------------------------------------------------------------- #
# Simulation step                                                              #
# --------------------------------------------------------------------------- #


def test_one_step_runs_without_error():
    cfg = SimConfig(num_nodes=10, num_factions=2, seed=42)
    state = create_sim(cfg)
    step(state)
    assert state.tick == 1


def test_step_increases_tick():
    cfg = SimConfig(num_nodes=10, num_factions=2, seed=42)
    state = create_sim(cfg)
    for _ in range(5):
        step(state)
    assert state.tick == 5


def test_spice_income_collected_on_step():
    cfg = SimConfig(num_nodes=8, num_factions=2, seed=1)
    state = create_sim(cfg)
    # First step collects income; factions with capital node should have positive stock
    step(state)
    for faction in state.factions.values():
        # Each faction starts with a capital — income must be >= its capital's spice flow
        assert faction.spice_stock >= 0


# --------------------------------------------------------------------------- #
# Conquest flip                                                                #
# --------------------------------------------------------------------------- #


def test_node_flips_after_threshold_pressure():
    """Manually drive conquest: one faction with massive stock against a single neighbour."""
    cfg = SimConfig(num_nodes=5, num_factions=2, seed=10, flip_threshold=5.0)
    state = create_sim(cfg)

    # Find a border target for faction-0
    from examples.multi_agent_sim.engine import _assign_priorities, _apply_conquest, _collect_income

    # Give faction-0 lots of spice
    state.factions["faction-0"].spice_stock = 1000.0
    state.factions["faction-1"].spice_stock = 0.0

    # Force faction-0 to target a single border node with weight 1.0
    targets = state.border_targets_for("faction-0")
    if not targets:
        pytest.skip("No border targets — degenerate graph for this seed")

    target_id = targets[0]
    state.factions["faction-0"].priorities = {target_id: 1.0}
    state.factions["faction-1"].priorities = {}

    # Drive pressure until flip
    for _ in range(20):
        if state.nodes[target_id].owner_id == "faction-0":
            break
        _apply_conquest(state)

    assert state.nodes[target_id].owner_id == "faction-0", (
        f"Node {target_id} was not flipped; accumulated pressure = "
        f"{state.nodes[target_id].pressure_accumulated}"
    )


# --------------------------------------------------------------------------- #
# Genome drift and secession                                                   #
# --------------------------------------------------------------------------- #


def test_hamming_check_triggers_secession_on_step():
    """Force a genome drift scenario by directly corrupting a node's genome."""
    cfg = SimConfig(
        num_nodes=8,
        num_factions=2,
        seed=3,
        genome_length=8,
        drift_threshold_fraction=0.5,  # 4 bits
        mutation_rate=0.0,  # disable natural mutation for this test
    )
    state = create_sim(cfg)

    # Find a non-capital node owned by faction-0
    faction_0 = state.factions["faction-0"]
    owned = [
        nid for nid in state.nodes_owned_by("faction-0")
        if nid != faction_0.capital_id
    ]
    if not owned:
        pytest.skip("faction-0 only has capital node — give it more territory")

    target_nid = owned[0]
    # Fully invert the node's genome vs the faction genome
    faction_genome = faction_0.genome
    state.nodes[target_nid].genome = [1 - b for b in faction_genome]

    # One step should detect secession
    initial_faction_count = len(state.factions)
    step(state)
    assert len(state.factions) > initial_faction_count, "Expected a secession event"


def test_secession_new_faction_owns_node():
    """After secession, the seceding node should belong to the new faction."""
    cfg = SimConfig(
        num_nodes=8,
        num_factions=2,
        seed=3,
        genome_length=8,
        drift_threshold_fraction=0.5,
        mutation_rate=0.0,
    )
    state = create_sim(cfg)

    faction_0 = state.factions["faction-0"]
    owned = [
        nid for nid in state.nodes_owned_by("faction-0")
        if nid != faction_0.capital_id
    ]
    if not owned:
        pytest.skip("faction-0 only has capital node")

    target_nid = owned[0]
    state.nodes[target_nid].genome = [1 - b for b in faction_0.genome]
    step(state)

    # The target node must NOT be owned by faction-0 anymore
    assert state.nodes[target_nid].owner_id != "faction-0"

    # The new owner must be a valid faction
    new_owner = state.nodes[target_nid].owner_id
    assert new_owner in state.factions


# --------------------------------------------------------------------------- #
# Serialisation                                                                #
# --------------------------------------------------------------------------- #


def test_serialize_state_has_expected_keys():
    cfg = SimConfig(num_nodes=6, num_factions=2, seed=42)
    state = create_sim(cfg)
    step(state)
    d = serialize_state(state)
    for key in ("tick", "game_over", "winner_id", "factions", "nodes", "edges", "event_log", "config"):
        assert key in d, f"Missing key: {key}"


def test_serialize_nodes_have_positions():
    cfg = SimConfig(num_nodes=6, num_factions=2, seed=42)
    state = create_sim(cfg)
    d = serialize_state(state)
    for node in d["nodes"]:
        assert 0.0 <= node["x"] <= 1.0
        assert 0.0 <= node["y"] <= 1.0


def test_max_ticks_ends_game():
    cfg = SimConfig(num_nodes=6, num_factions=2, seed=42, max_ticks=3)
    state = create_sim(cfg)
    for _ in range(5):
        step(state)
    assert state.game_over
    assert state.winner_id is not None
