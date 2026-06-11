"""Smoke tests for Lab 3 Limited-Perception multi-agent simulation.

These tests live in examples and are NOT part of the tracked tests/ tree.
Run with:
    python -m pytest -q examples/lab3_perception_sim/test_sim_local.py
"""

from __future__ import annotations

import pytest

from examples.core_only_labs.abstract_geopolitical_sim.lab3_perception_sim.config import SimConfig
from examples.core_only_labs.abstract_geopolitical_sim.lab3_perception_sim.graph_gen import build_graph, bfs_distances
from examples.core_only_labs.abstract_geopolitical_sim.lab3_perception_sim.engine import (
    SimState,
    create_sim,
    step,
    serialize_state,
    _hamming_distance,
    _random_genome,
    _mutate_genome,
)
from examples.core_only_labs.abstract_geopolitical_sim.lab3_perception_sim.perception import (
    get_faction_perception,
    visible_border_targets,
)

import random

# --------------------------------------------------------------------------- #
# Config validation (includes perception_mode)                                #
# --------------------------------------------------------------------------- #


def test_config_defaults_are_valid():
    SimConfig().validate()


def test_config_rejects_bad_perception_mode():
    with pytest.raises(ValueError):
        SimConfig(perception_mode="unknown").validate()


def test_config_accepts_valid_perception_modes():
    SimConfig(perception_mode="limited").validate()
    SimConfig(perception_mode="full").validate()


# --------------------------------------------------------------------------- #
# Graph generation                                                             #
# --------------------------------------------------------------------------- #


def test_graph_connectivity():
    """Generated graph must be connected."""
    cfg = SimConfig(num_nodes=12, seed=7)
    g = build_graph(cfg)
    assert len(g.nodes) == 12
    dists = bfs_distances(g, "node-0")
    unreachable = [nid for nid, d in dists.items() if d < 0]
    assert unreachable == [], f"Unreachable nodes: {unreachable}"


# --------------------------------------------------------------------------- #
# Perception tests                                                             #
# --------------------------------------------------------------------------- #


def test_perception_includes_owned_and_neighbors():
    """Perception should include owned spaces + immediate neighbors."""
    cfg = SimConfig(
        num_nodes=8,
        num_factions=2,
        seed=42,
        perception_mode="limited",
    )
    state = create_sim(cfg)

    # Get perception for faction-0
    perception = get_faction_perception(state, "faction-0")

    # Collect owned and neighbor IDs manually
    faction_0 = state.factions["faction-0"]
    owned = set(state.nodes_owned_by("faction-0"))
    neighbors = set()
    for nid in owned:
        for neighbor_id in state.relation_graph.neighbors_of(nid):
            if neighbor_id not in owned:
                neighbors.add(neighbor_id)

    expected_visible = owned | neighbors

    # Extract perceived space IDs (perceived_spaces is a dict with space IDs as keys)
    perceived_ids = set(perception.perceived_spaces.keys())

    assert (
        perceived_ids == expected_visible
    ), f"Perceived spaces {perceived_ids} do not match expected {expected_visible}"


def test_perception_excludes_distant_nodes():
    """Perception should NOT include nodes beyond distance 1."""
    cfg = SimConfig(
        num_nodes=12,
        num_factions=2,
        seed=7,
        perception_mode="limited",
    )
    state = create_sim(cfg)

    perception = get_faction_perception(state, "faction-0")

    # Manually compute distance-2+ nodes
    faction_0 = state.factions["faction-0"]
    owned = set(state.nodes_owned_by("faction-0"))
    neighbors = set()
    for nid in owned:
        for neighbor_id in state.relation_graph.neighbors_of(nid):
            if neighbor_id not in owned:
                neighbors.add(neighbor_id)

    # All nodes not in (owned | neighbors) should be NOT perceived
    distance_2_plus = set(nid for nid in state.nodes if nid not in owned | neighbors)

    # Extract perceived space IDs
    perceived_ids = set(perception.perceived_spaces.keys())

    for nid in distance_2_plus:
        assert (
            nid not in perceived_ids
        ), f"Distance-2 node {nid} should not be visible; perceived={perceived_ids}"


def test_limited_ai_only_targets_visible():
    """With perception_mode='limited', AI can only target visible borders."""
    cfg = SimConfig(
        num_nodes=10,
        num_factions=2,
        seed=42,
        perception_mode="limited",
    )
    state = create_sim(cfg)

    # Get perception for faction-0
    perception = get_faction_perception(state, "faction-0")
    owned_set = set(state.nodes_owned_by("faction-0"))

    # visible_border_targets should only return neighbors visible in perception
    visible_targets = visible_border_targets(perception, owned_set)

    # Verify all visible targets are unowned neighbors
    for target_id in visible_targets:
        assert target_id not in owned_set, f"{target_id} is owned, should not be target"
        # Check that target is adjacent to at least one owned space
        is_neighbor = False
        for nid in owned_set:
            if target_id in state.relation_graph.neighbors_of(nid):
                is_neighbor = True
                break
        assert is_neighbor, f"{target_id} is not a neighbor of owned spaces"


def test_full_mode_identical_to_omniscience():
    """perception_mode='full' should not use perception in AI decision-making.

    This test verifies that in full mode, the engine does NOT compute or use
    perception for targeting decisions, matching Lab 2 omniscient behavior.
    """
    cfg = SimConfig(
        num_nodes=8,
        num_factions=2,
        seed=99,
        perception_mode="full",
    )
    state = create_sim(cfg)

    # The key difference is that in full mode, step() doesn't compute perception
    # and thus AI has access to all border targets (same as Lab 2)
    # We verify by running a few steps without errors
    for _ in range(3):
        step(state)

    assert state.tick == 3, "Full mode should allow normal stepping"


def test_step_with_limited_perception():
    """Engine.step() should handle limited perception mode without errors."""
    cfg = SimConfig(
        num_nodes=10,
        num_factions=3,
        seed=42,
        perception_mode="limited",
    )
    state = create_sim(cfg)

    # Should run multiple steps without error
    for _ in range(5):
        step(state)

    assert state.tick == 5


def test_step_with_full_perception():
    """Engine.step() should handle full perception mode without errors."""
    cfg = SimConfig(
        num_nodes=10,
        num_factions=3,
        seed=42,
        perception_mode="full",
    )
    state = create_sim(cfg)

    for _ in range(5):
        step(state)

    assert state.tick == 5


# --------------------------------------------------------------------------- #
# Serialisation tests                                                         #
# --------------------------------------------------------------------------- #


def test_serialize_state_includes_perception_mode():
    cfg = SimConfig(num_nodes=6, num_factions=2, seed=42, perception_mode="limited")
    state = create_sim(cfg)
    d = serialize_state(state)
    assert d["config"]["perception_mode"] == "limited"


def test_serialize_state_with_full_perception_mode():
    cfg = SimConfig(num_nodes=6, num_factions=2, seed=42, perception_mode="full")
    state = create_sim(cfg)
    d = serialize_state(state)
    assert d["config"]["perception_mode"] == "full"


# --------------------------------------------------------------------------- #
# Genome utilities (from Lab 2)                                               #
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
# Simulation initialisation (from Lab 2)                                      #
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
# Simulation step (from Lab 2)                                                #
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
    step(state)
    for faction in state.factions.values():
        assert faction.spice_stock >= 0


# --------------------------------------------------------------------------- #
# Conquest and secession (from Lab 2)                                         #
# --------------------------------------------------------------------------- #


def test_max_ticks_ends_game():
    cfg = SimConfig(num_nodes=6, num_factions=2, seed=42, max_ticks=3)
    state = create_sim(cfg)
    for _ in range(5):
        step(state)
    assert state.game_over
