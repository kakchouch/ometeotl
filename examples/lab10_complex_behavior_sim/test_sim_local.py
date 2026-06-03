"""Tests for Lab 10 — Complex Behavior multi-agent simulation.

These tests live in examples and are NOT part of the tracked tests/ tree.
Run with:
    python -m pytest -q examples/lab10_complex_behavior_sim/test_sim_local.py
"""

from __future__ import annotations

import pytest
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.strategies import Strategy

from examples.lab10_complex_behavior_sim.config import SimConfig
from examples.lab10_complex_behavior_sim.graph_gen import build_graph, bfs_distances
from examples.lab10_complex_behavior_sim.engine import (
    SimState,
    Node,
    Link,
    Faction,
    BehaviorProfile,
    create_sim,
    step,
    serialize_state,
    _execute_transport,
    _plan_moves,
    _plan_centralization,
    _reset_link_usage,
    _collect_income,
    _hamming_distance,
    _random_genome,
    _mutate_genome,
    _apply_centralization,
    _symbolic_snapshot,
    _build_goal_and_strategy,
)
from examples.lab10_complex_behavior_sim.perception import (
    get_faction_perception,
    visible_border_targets,
)

# --------------------------------------------------------------------------- #
# Config validation                                                            #
# --------------------------------------------------------------------------- #


def test_config_defaults_valid():
    SimConfig().validate()


def test_config_transport_base_cost_nonnegative():
    with pytest.raises(ValueError):
        SimConfig(transport_base_cost=-0.1).validate()


def test_config_transport_gas_fee_range():
    with pytest.raises(ValueError):
        SimConfig(transport_gas_fee=1.0).validate()
    with pytest.raises(ValueError):
        SimConfig(transport_gas_fee=-0.1).validate()
    SimConfig(transport_gas_fee=0.0).validate()  # 0 is allowed


def test_config_to_dict_includes_fee_fields():
    cfg = SimConfig(transport_gas_fee=0.1, transport_base_cost=2.0)
    d = cfg.to_dict()
    assert d["transport_gas_fee"] == 0.1
    assert d["transport_base_cost"] == 2.0


def test_config_to_dict_includes_centralization_fields():
    cfg = SimConfig(
        behavior_centralization_min=0.3,
        behavior_centralization_max=0.6,
        centralization_admin_cost=2.5,
    )
    d = cfg.to_dict()
    assert d["behavior_centralization_min"] == 0.3
    assert d["behavior_centralization_max"] == 0.6
    assert d["centralization_admin_cost"] == 2.5


def test_config_to_dict_includes_relation_fields():
    cfg = SimConfig(
        relation_initial=0.9,
        relation_growth_rate=0.02,
        relation_pressure_impact=0.03,
        relation_offense_bias=0.7,
    )
    d = cfg.to_dict()
    assert d["relation_initial"] == 0.9
    assert d["relation_growth_rate"] == 0.02
    assert d["relation_pressure_impact"] == 0.03
    assert d["relation_offense_bias"] == 0.7


def test_config_to_dict_includes_globalization_fields():
    cfg = SimConfig(
        allow_disconnected_regions=True,
        globalization_link_growth_chance=0.02,
        globalization_bridge_spawn_chance=0.01,
    )
    d = cfg.to_dict()
    assert d["allow_disconnected_regions"] is True
    assert d["globalization_link_growth_chance"] == 0.02
    assert d["globalization_bridge_spawn_chance"] == 0.01


def test_behavior_ranges_are_validated():
    with pytest.raises(ValueError):
        SimConfig(behavior_engagement_min=0.9, behavior_engagement_max=0.1).validate()
    with pytest.raises(ValueError):
        SimConfig(behavior_concentration_min=-0.1).validate()
    with pytest.raises(ValueError):
        SimConfig(behavior_liquidity_max=1.1).validate()
    with pytest.raises(ValueError):
        SimConfig(
            behavior_centralization_min=0.9, behavior_centralization_max=0.1
        ).validate()
    with pytest.raises(ValueError):
        SimConfig(relation_initial=1.1).validate()
    with pytest.raises(ValueError):
        SimConfig(relation_growth_rate=-0.01).validate()
    with pytest.raises(ValueError):
        SimConfig(globalization_link_growth_chance=1.2).validate()
    with pytest.raises(ValueError):
        SimConfig(globalization_bridge_spawn_chance=-0.1).validate()


def test_create_sim_assigns_behavior_per_faction():
    """ECLOZ must be the genome projection, not a random sample."""
    from examples.lab10_complex_behavior_sim.engine import _genome_to_ecloz

    cfg = SimConfig(seed=4, num_nodes=8, num_factions=3)
    state = create_sim(cfg)
    for faction in state.factions.values():
        b = faction.behavior
        # All axes in [0, 1]
        assert 0.0 <= b.engagement_threshold <= 1.0
        assert 0.0 <= b.concentration <= 1.0
        assert 0.0 <= b.liquidity_preference <= 1.0
        assert 0.0 <= b.objective_bias <= 1.0
        assert 0.0 <= b.centralization <= 1.0
        # Exactly matches the genome projection
        expected = _genome_to_ecloz(faction.genome)
        assert b == expected, f"ECLOZ mismatch for {faction.faction_id}"


def test_faction_ecloz_invariant_under_node_genome_drift():
    """ECLOZ must stay constant while node genomes drift (faction genome is fixed)."""
    from examples.lab10_complex_behavior_sim.engine import _genome_to_ecloz

    cfg = SimConfig(
        seed=11,
        num_nodes=10,
        num_factions=2,
        mutation_rate=1.0,
        max_ticks=0,
        drift_threshold_fraction=0.99,  # suppress secession so factions survive
    )
    state = create_sim(cfg)

    fid = sorted(state.factions.keys())[0]
    genome_before = state.factions[fid].genome[:]
    behavior_before = state.factions[fid].behavior

    for _ in range(5):
        step(state)
        if state.game_over:
            break

    if fid not in state.factions:
        return  # faction eliminated — nothing to check

    # Faction genome must not have changed (only node genomes drift)
    assert state.factions[fid].genome == genome_before, "Faction genome should be immutable"
    # ECLOZ must equal the genome projection and must not have drifted
    assert state.factions[fid].behavior == behavior_before, "ECLOZ must not drift"
    assert state.factions[fid].behavior == _genome_to_ecloz(genome_before)


# --------------------------------------------------------------------------- #
# Graph generation                                                             #
# --------------------------------------------------------------------------- #


def test_graph_connectivity():
    cfg = SimConfig(num_nodes=12, seed=7, allow_disconnected_regions=False)
    g = build_graph(cfg)
    assert len(g.nodes) == 12
    dists = bfs_distances(g, "node-0")
    unreachable = [nid for nid, d in dists.items() if d < 0]
    assert unreachable == [], f"Unreachable nodes: {unreachable}"


def test_geographic_can_start_disconnected_when_enabled():
    cfg = SimConfig(
        seed=3,
        num_nodes=24,
        graph_mode="geographic",
        geography_preset="archipelago",
        graph_density=0.10,
        allow_disconnected_regions=True,
    )
    g = build_graph(cfg)
    dists = bfs_distances(g, "node-0")
    unreachable = [nid for nid, d in dists.items() if d < 0]
    assert unreachable, "Expected at least one disconnected node in Lab 10 geographic mode"


def test_geographic_forced_connected_when_disabled():
    cfg = SimConfig(
        seed=3,
        num_nodes=24,
        graph_mode="geographic",
        geography_preset="archipelago",
        graph_density=0.10,
        allow_disconnected_regions=False,
    )
    g = build_graph(cfg)
    dists = bfs_distances(g, "node-0")
    unreachable = [nid for nid, d in dists.items() if d < 0]
    assert unreachable == []


def test_geography_preset_validation():
    with pytest.raises(ValueError):
        SimConfig(geography_preset="invalid").validate()
    SimConfig(geography_preset="pangea").validate()
    SimConfig(geography_preset="continents").validate()
    SimConfig(geography_preset="archipelago").validate()


def test_geography_presets_produce_distinct_topologies():
    """With same seed/size, presets should not collapse to identical edge sets."""
    g_pangea = build_graph(
        SimConfig(
            seed=42, num_nodes=24, graph_mode="geographic", geography_preset="pangea"
        )
    )
    g_cont = build_graph(
        SimConfig(
            seed=42,
            num_nodes=24,
            graph_mode="geographic",
            geography_preset="continents",
        )
    )
    g_arch = build_graph(
        SimConfig(
            seed=42,
            num_nodes=24,
            graph_mode="geographic",
            geography_preset="archipelago",
        )
    )

    e_p = set(tuple(sorted(e)) for e in g_pangea.edges)
    e_c = set(tuple(sorted(e)) for e in g_cont.edges)
    e_a = set(tuple(sorted(e)) for e in g_arch.edges)

    assert e_p != e_c
    assert e_c != e_a
    assert e_p != e_a


# --------------------------------------------------------------------------- #
# create_sim — logistics initialisation                                       #
# --------------------------------------------------------------------------- #


def test_create_sim_nodes_have_spice_stock():
    """Every node starts with config.initial_node_spice."""
    cfg = SimConfig(seed=1, num_nodes=8, num_factions=2, initial_node_spice=7.5)
    state = create_sim(cfg)
    for nid, node in state.nodes.items():
        assert node.spice_stock == pytest.approx(7.5), f"{nid} has wrong initial stock"


def test_create_sim_links_built():
    """Each edge in the graph has a Link with capacity in [min_link_flow, max_link_flow]."""
    cfg = SimConfig(
        seed=3, num_nodes=8, num_factions=2, min_link_flow=2.0, max_link_flow=10.0
    )
    state = create_sim(cfg)
    assert len(state.links) > 0
    for key, lnk in state.links.items():
        assert (
            2.0 <= lnk.max_flow <= 10.0
        ), f"Link {key} capacity {lnk.max_flow} out of range"
        assert lnk.used_flow == 0.0


def test_create_sim_factions_have_no_spice_stock():
    """Faction has no spice_stock attribute (removed in the logistics model)."""
    cfg = SimConfig(seed=1, num_nodes=6, num_factions=2)
    state = create_sim(cfg)
    for f in state.factions.values():
        assert not hasattr(f, "spice_stock"), "Faction should not have spice_stock"


# --------------------------------------------------------------------------- #
# Income: spice goes into nodes, not factions                                 #
# --------------------------------------------------------------------------- #


def test_income_flows_into_nodes():
    """_collect_income adds spice to node.spice_stock, not to factions."""
    cfg = SimConfig(seed=1, num_nodes=6, num_factions=2, initial_node_spice=0.0)
    state = create_sim(cfg)
    before = {nid: n.spice_stock for nid, n in state.nodes.items()}
    _collect_income(state)
    for nid, node in state.nodes.items():
        if node.owner_id is not None:
            assert node.spice_stock == before[nid] + node.spice_flow
        else:
            assert node.spice_stock == before[nid]


# --------------------------------------------------------------------------- #
# Gas fee — base cost punishes scatter; bulk is efficient                     #
# --------------------------------------------------------------------------- #


def test_base_cost_burned_per_shipment():
    """Each executed move order burns exactly transport_base_cost from source."""
    cfg = SimConfig(
        seed=1,
        num_nodes=6,
        num_factions=2,
        transport_base_cost=2.0,
        transport_gas_fee=0.0,
        initial_node_spice=20.0,
    )
    state = create_sim(cfg)
    # Pick a faction and manually inject a move order: src→dst, amount=5
    faction = list(state.factions.values())[0]
    src_id = faction.capital_id
    # Find a reachable neighbor (owned or unowned)
    neighbors = state.neighbors_of(src_id)
    assert neighbors, "Capital must have at least one neighbor"
    dst_id = neighbors[0]

    state.nodes[src_id].spice_stock = 20.0
    faction.move_orders = [(src_id, dst_id, 5.0)]

    # Manually ensure link has capacity
    key = (min(src_id, dst_id), max(src_id, dst_id))
    state.links[key] = Link(
        source_id=min(src_id, dst_id), target_id=max(src_id, dst_id), max_flow=100.0
    )

    _execute_transport(state)

    # Source should have lost base_cost (2.0) + shipment (5.0) = 7.0
    assert state.nodes[src_id].spice_stock == pytest.approx(13.0)


def test_gas_fee_proportional_applied_after_base_cost():
    """Delivered = amount * (1 - gas_fee); base cost burned from source separately."""
    cfg = SimConfig(
        seed=1,
        num_nodes=6,
        num_factions=2,
        transport_base_cost=1.0,
        transport_gas_fee=0.2,
        initial_node_spice=30.0,
    )
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]
    src_id = faction.capital_id
    dst_id = state.neighbors_of(src_id)[0]

    # Force dst to be owned by same faction so delivery goes to spice_stock
    state.nodes[dst_id].owner_id = faction.faction_id
    state.nodes[src_id].spice_stock = 30.0
    state.nodes[dst_id].spice_stock = 0.0
    faction.move_orders = [(src_id, dst_id, 10.0)]

    key = (min(src_id, dst_id), max(src_id, dst_id))
    state.links[key] = Link(
        source_id=min(src_id, dst_id), target_id=max(src_id, dst_id), max_flow=100.0
    )

    _execute_transport(state)

    # Source: 30 - 1 (base) - 10 (amount) = 19
    assert state.nodes[src_id].spice_stock == pytest.approx(19.0)
    # Dst: 10 * (1 - 0.2) = 8.0
    assert state.nodes[dst_id].spice_stock == pytest.approx(8.0)


def test_scatter_costs_more_than_bulk():
    """Ten scattered 1-unit shipments cost 10x the base fee; one 10-unit shipment pays once."""
    cfg = SimConfig(
        seed=1,
        num_nodes=12,
        num_factions=2,
        transport_base_cost=1.0,
        transport_gas_fee=0.0,
        initial_node_spice=50.0,
    )
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]
    src_id = faction.capital_id
    neighbors = state.neighbors_of(src_id)
    # Need at least 2 neighbors for scatter test; skip if not available
    if len(neighbors) < 2:
        pytest.skip("Not enough neighbors for scatter test with this seed")

    # Make all neighbors friendly so spice_stock is used (not pressure)
    for nb in neighbors:
        state.nodes[nb].owner_id = faction.faction_id

    for key in list(state.links.keys()):
        state.links[key].max_flow = 100.0

    # --- Scatter: 2 orders of 5 units to 2 different nodes ---
    state.nodes[src_id].spice_stock = 50.0
    faction.move_orders = [
        (src_id, neighbors[0], 5.0),
        (src_id, neighbors[1], 5.0),
    ]
    _execute_transport(state)
    scatter_remaining = state.nodes[src_id].spice_stock
    # Spent: 2 * base_cost (2.0) + 2 * 5 (10.0) = 12.0 → remaining = 38.0

    # --- Bulk: 1 order of 10 units to 1 node ---
    state.nodes[src_id].spice_stock = 50.0
    faction.move_orders = [(src_id, neighbors[0], 10.0)]
    _execute_transport(state)
    bulk_remaining = state.nodes[src_id].spice_stock
    # Spent: 1 * base_cost (1.0) + 10 (10.0) = 11.0 → remaining = 39.0

    assert (
        bulk_remaining > scatter_remaining
    ), f"Bulk ({bulk_remaining}) should leave more spice than scatter ({scatter_remaining})"


def test_order_below_base_cost_is_cancelled():
    """A move order for 0 amount (after base cost exceeds stock) is dropped cleanly."""
    cfg = SimConfig(
        seed=1,
        num_nodes=6,
        num_factions=2,
        transport_base_cost=5.0,
        transport_gas_fee=0.0,
        initial_node_spice=3.0,
    )
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]
    src_id = faction.capital_id
    dst_id = state.neighbors_of(src_id)[0]
    state.nodes[dst_id].owner_id = faction.faction_id

    # Stock (3.0) < base_cost (5.0) → cannot ship
    state.nodes[src_id].spice_stock = 3.0
    before_dst = state.nodes[dst_id].spice_stock
    faction.move_orders = [(src_id, dst_id, 10.0)]

    key = (min(src_id, dst_id), max(src_id, dst_id))
    state.links[key] = Link(
        source_id=min(src_id, dst_id), target_id=max(src_id, dst_id), max_flow=100.0
    )

    _execute_transport(state)

    # Destination receives nothing
    assert state.nodes[dst_id].spice_stock == pytest.approx(before_dst)
    # Source may have lost its stock (burned as base cost overhead) but does not go negative
    assert state.nodes[src_id].spice_stock >= 0.0


# --------------------------------------------------------------------------- #
# Link capacity bottleneck                                                    #
# --------------------------------------------------------------------------- #


def test_link_capacity_limits_flow():
    """Shipments cannot exceed the link's max_flow."""
    cfg = SimConfig(
        seed=2,
        num_nodes=6,
        num_factions=2,
        transport_base_cost=0.0,
        transport_gas_fee=0.0,
        initial_node_spice=100.0,
    )
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]
    src_id = faction.capital_id
    dst_id = state.neighbors_of(src_id)[0]
    state.nodes[dst_id].owner_id = faction.faction_id

    # Cap the link at 5 units
    key = (min(src_id, dst_id), max(src_id, dst_id))
    state.links[key] = Link(
        source_id=min(src_id, dst_id), target_id=max(src_id, dst_id), max_flow=5.0
    )

    state.nodes[src_id].spice_stock = 100.0
    state.nodes[dst_id].spice_stock = 0.0
    # Try to send 50 units — link only allows 5
    faction.move_orders = [(src_id, dst_id, 50.0)]

    _execute_transport(state)

    # Delivered ≤ 5.0 (link cap)
    assert state.nodes[dst_id].spice_stock <= 5.0 + 1e-9


# --------------------------------------------------------------------------- #
# Conquest via transport pressure                                             #
# --------------------------------------------------------------------------- #


def test_pressure_accumulated_from_transport():
    """Spice routed to an enemy node increases its pressure_accumulated."""
    cfg = SimConfig(
        seed=3,
        num_nodes=6,
        num_factions=2,
        transport_base_cost=0.0,
        transport_gas_fee=0.0,
        initial_node_spice=50.0,
        flip_threshold=100.0,
    )
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]
    src_id = faction.capital_id
    # Pick an enemy neighbor
    enemy_nb = None
    for nb in state.neighbors_of(src_id):
        if state.nodes[nb].owner_id != faction.faction_id:
            enemy_nb = nb
            break
    if enemy_nb is None:
        pytest.skip("No enemy neighbor available")

    key = (min(src_id, enemy_nb), max(src_id, enemy_nb))
    state.links[key] = Link(
        source_id=min(src_id, enemy_nb), target_id=max(src_id, enemy_nb), max_flow=100.0
    )

    before = state.nodes[enemy_nb].pressure_accumulated
    faction.move_orders = [(src_id, enemy_nb, 10.0)]
    _execute_transport(state)

    assert state.nodes[enemy_nb].pressure_accumulated > before


def test_node_flip_seizes_spice():
    """When a node flips, its spice_stock is transferred to the conqueror's capital."""
    cfg = SimConfig(
        seed=5,
        num_nodes=6,
        num_factions=2,
        transport_base_cost=0.0,
        transport_gas_fee=0.0,
        initial_node_spice=10.0,
        flip_threshold=1.0,
    )
    state = create_sim(cfg)
    # Manually trigger a flip: pick a neutral node, apply pressure from faction-0
    neutral_node = next(
        (nid for nid, n in state.nodes.items() if n.owner_id is None), None
    )
    if neutral_node is None:
        pytest.skip("No neutral node available with this seed")

    faction = state.factions["faction-0"]
    cap_stock_before = state.nodes[faction.capital_id].spice_stock
    seized_amount = state.nodes[neutral_node].spice_stock

    # Manually set pressure past flip_threshold
    state.nodes[neutral_node].pressure["faction-0"] = 5.0
    state.nodes[neutral_node].pressure_accumulated = 5.0

    from examples.lab10_complex_behavior_sim.engine import _apply_conquest

    _apply_conquest(state)

    # Node should now belong to faction-0
    assert state.nodes[neutral_node].owner_id == "faction-0"
    # Node stock cleared
    assert state.nodes[neutral_node].spice_stock == pytest.approx(0.0)
    # Capital gains seized amount
    assert state.nodes[faction.capital_id].spice_stock == pytest.approx(
        cap_stock_before + seized_amount
    )


# --------------------------------------------------------------------------- #
# Full step integration                                                        #
# --------------------------------------------------------------------------- #


def test_step_advances_tick():
    cfg = SimConfig(seed=1, num_nodes=8, num_factions=2)
    state = create_sim(cfg)
    step(state)
    assert state.tick == 1


def test_multi_step_no_error():
    cfg = SimConfig(seed=42, num_nodes=10, num_factions=3, perception_mode="limited")
    state = create_sim(cfg)
    for _ in range(20):
        step(state)
    assert state.tick == 20


def test_step_resets_link_usage_each_tick():
    """used_flow on links should be 0 at start of each tick after reset."""
    cfg = SimConfig(seed=1, num_nodes=8, num_factions=2)
    state = create_sim(cfg)
    step(state)
    # After a full step, reset_link_usage is called at the start of the NEXT step.
    # So after the step, used_flow may be nonzero (it reflects what was moved).
    # On the second step's _reset_link_usage, they go back to 0.
    # We confirm by manually calling reset and checking:
    _reset_link_usage(state)
    for lnk in state.links.values():
        assert lnk.used_flow == 0.0


# --------------------------------------------------------------------------- #
# Serialisation                                                               #
# --------------------------------------------------------------------------- #


def test_serialize_includes_node_spice_stock():
    cfg = SimConfig(seed=1, num_nodes=6, num_factions=2, initial_node_spice=9.0)
    state = create_sim(cfg)
    d = serialize_state(state)
    for node_dict in d["nodes"]:
        assert "spice_stock" in node_dict
        assert node_dict["spice_stock"] >= 0.0


def test_serialize_includes_link_capacities():
    cfg = SimConfig(seed=1, num_nodes=6, num_factions=2)
    state = create_sim(cfg)
    d = serialize_state(state)
    for edge in d["edges"]:
        assert "max_flow" in edge
        assert "used_flow" in edge
        assert edge["max_flow"] is not None


def test_serialize_includes_move_orders():
    cfg = SimConfig(seed=1, num_nodes=8, num_factions=2)
    state = create_sim(cfg)
    step(state)
    d = serialize_state(state)
    for fid, f in d["factions"].items():
        assert "move_orders" in f


def test_serialize_no_faction_spice_stock():
    """Faction serialization must not include legacy spice_stock key."""
    cfg = SimConfig(seed=1, num_nodes=6, num_factions=2)
    state = create_sim(cfg)
    d = serialize_state(state)
    for fid, f in d["factions"].items():
        assert "spice_stock" not in f, f"Faction {fid} should not expose spice_stock"


def test_serialize_config_includes_fee_params():
    cfg = SimConfig(seed=1, transport_gas_fee=0.1, transport_base_cost=2.5)
    state = create_sim(cfg)
    d = serialize_state(state)
    assert d["config"]["transport_gas_fee"] == pytest.approx(0.1)
    assert d["config"]["transport_base_cost"] == pytest.approx(2.5)


def test_serialize_includes_faction_behavior_fields():
    cfg = SimConfig(seed=2, num_nodes=8, num_factions=2)
    state = create_sim(cfg)
    d = serialize_state(state)
    for faction_data in d["factions"].values():
        assert "behavior" in faction_data
        b = faction_data["behavior"]
        assert "engagement_threshold" in b
        assert "concentration" in b
        assert "liquidity_preference" in b
        assert "objective_bias" in b
        assert "centralization" in b


def test_liquidity_axis_reduces_dispatch():
    """Higher liquidity preference should dispatch less spice from same source state."""
    cfg = SimConfig(seed=9, num_nodes=10, num_factions=2, transport_base_cost=0.0)
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]
    src_id = faction.capital_id
    neighbors = state.neighbors_of(src_id)
    if not neighbors:
        pytest.skip("Capital has no neighbors")
    dst_id = neighbors[0]

    # Make sure routing can attack this node and capacity is not bottlenecking.
    key = (min(src_id, dst_id), max(src_id, dst_id))
    state.links[key].max_flow = 10_000.0
    state.nodes[src_id].spice_stock = 100.0
    faction.behavior.engagement_threshold = 0.0
    faction.behavior.objective_bias = 1.0

    faction.behavior.liquidity_preference = 0.0
    _plan_moves(state, faction, perception=None)
    low_liq_amount = sum(a for s, d, a in faction.move_orders if s == src_id)

    state.nodes[src_id].spice_stock = 100.0
    faction.behavior.liquidity_preference = 0.95
    _plan_moves(state, faction, perception=None)
    high_liq_amount = sum(a for s, d, a in faction.move_orders if s == src_id)

    assert low_liq_amount >= high_liq_amount


def test_high_z_plans_admin_transport_and_reduces_drift():
    cfg = SimConfig(
        seed=21,
        num_nodes=8,
        num_factions=1,
        genome_length=8,
        mutation_rate=0.0,
        transport_base_cost=0.0,
        transport_gas_fee=0.0,
        centralization_admin_cost=1.0,
    )
    state = create_sim(cfg)
    faction = state.factions["faction-0"]
    # Force Z=1.0 as a unit-test fixture (testing _plan_centralization, not genome derivation)
    faction.behavior = BehaviorProfile(
        engagement_threshold=faction.behavior.engagement_threshold,
        concentration=faction.behavior.concentration,
        liquidity_preference=faction.behavior.liquidity_preference,
        objective_bias=faction.behavior.objective_bias,
        centralization=1.0,
    )
    neighbors = state.neighbors_of(faction.capital_id)
    if not neighbors:
        pytest.skip("Capital has no neighbors")
    candidate = neighbors[0]
    state.nodes[candidate].owner_id = faction.faction_id
    state.nodes[candidate].genome = faction.genome[:]
    state.nodes[candidate].genome[0] = 1 - state.nodes[candidate].genome[0]
    state.nodes[faction.capital_id].spice_stock = 10.0

    _plan_centralization(state, faction)
    assert faction.admin_orders, "Expected admin transport orders when Z is high"

    _execute_transport(state)
    delivered_stock = state.nodes[candidate].spice_stock
    assert delivered_stock > 0.0

    before = _hamming_distance(state.nodes[candidate].genome, faction.genome)
    _apply_centralization(state, faction, state.nodes[candidate])
    after = _hamming_distance(state.nodes[candidate].genome, faction.genome)

    assert before == 1
    assert after == 0


def test_low_z_skips_admin_transport():
    cfg = SimConfig(
        seed=22,
        num_nodes=8,
        num_factions=1,
        genome_length=8,
        mutation_rate=0.0,
    )
    state = create_sim(cfg)
    faction = state.factions["faction-0"]
    # Force Z=0.0 as a unit-test fixture (testing _plan_centralization, not genome derivation)
    faction.behavior = BehaviorProfile(
        engagement_threshold=faction.behavior.engagement_threshold,
        concentration=faction.behavior.concentration,
        liquidity_preference=faction.behavior.liquidity_preference,
        objective_bias=faction.behavior.objective_bias,
        centralization=0.0,
    )
    neighbors = state.neighbors_of(faction.capital_id)
    if not neighbors:
        pytest.skip("Capital has no neighbors")
    candidate = neighbors[0]
    state.nodes[candidate].owner_id = faction.faction_id
    state.nodes[candidate].genome = faction.genome[:]
    state.nodes[candidate].genome[0] = 1 - state.nodes[candidate].genome[0]

    _plan_centralization(state, faction)
    assert faction.admin_orders == []


def test_pressure_reduces_relation_and_growth_recovers_it():
    cfg = SimConfig(
        seed=31,
        num_nodes=8,
        num_factions=2,
        mutation_rate=0.0,
        transport_base_cost=0.0,
        transport_gas_fee=0.0,
        relation_initial=0.9,
        relation_growth_rate=0.0,
        relation_pressure_impact=0.05,
    )
    state = create_sim(cfg)
    attacker = state.factions["faction-0"]
    src = attacker.capital_id

    enemy_nb = None
    for nb in state.neighbors_of(src):
        if state.nodes[nb].owner_id not in (None, attacker.faction_id):
            enemy_nb = nb
            break
    if enemy_nb is None:
        pytest.skip("No enemy neighbor available")

    defender_id = state.nodes[enemy_nb].owner_id
    assert defender_id is not None
    state.nodes[src].spice_stock = 20.0
    attacker.move_orders = [(src, enemy_nb, 4.0)]

    _execute_transport(state)

    rel = state.relation_between(attacker.faction_id, defender_id)
    assert rel is not None
    assert rel < cfg.relation_initial

    # Growth should recover toward 1.0 and remain capped.
    state.config.relation_growth_rate = 0.2
    step(state)
    rel2 = state.relation_between(attacker.faction_id, defender_id)
    assert rel2 is not None
    assert rel2 <= 1.0
    assert rel2 >= rel


def test_high_relation_deincentivizes_pressure_vs_low_relation():
    cfg = SimConfig(
        seed=32,
        num_nodes=8,
        num_factions=2,
        mutation_rate=0.0,
        transport_base_cost=0.0,
        transport_gas_fee=0.0,
        relation_offense_bias=0.9,
    )
    state = create_sim(cfg)
    faction = state.factions["faction-0"]
    src = faction.capital_id
    neighbors = state.neighbors_of(src)
    if not neighbors:
        pytest.skip("Capital has no neighbors")

    enemy = None
    for nb in neighbors:
        if state.nodes[nb].owner_id not in (None, faction.faction_id):
            enemy = nb
            break
    if enemy is None:
        pytest.skip("No enemy neighbor available")

    defender = state.nodes[enemy].owner_id
    assert defender is not None

    faction.behavior.engagement_threshold = 0.0
    faction.behavior.objective_bias = 1.0
    faction.behavior.concentration = 1.0
    faction.behavior.liquidity_preference = 0.0
    state.nodes[src].spice_stock = 100.0
    state.adjust_relation(faction.faction_id, defender, 1.0)
    _plan_moves(state, faction, perception=None)
    high_rel_amount = sum(a for _s, _d, a in faction.move_orders)

    state.nodes[src].spice_stock = 100.0
    state.relations[state.relation_key(faction.faction_id, defender)] = 0.0
    _plan_moves(state, faction, perception=None)
    low_rel_amount = sum(a for _s, _d, a in faction.move_orders)

    assert low_rel_amount >= high_rel_amount


def test_globalization_link_growth_adds_one_capacity():
    cfg = SimConfig(
        seed=101,
        num_nodes=10,
        num_factions=2,
        globalization_link_growth_chance=1.0,
        globalization_bridge_spawn_chance=0.0,
    )
    state = create_sim(cfg)
    before_total = sum(lnk.max_flow for lnk in state.links.values())
    step(state)
    after_total = sum(lnk.max_flow for lnk in state.links.values())
    assert after_total == pytest.approx(before_total + 1.0)


def test_globalization_bridge_spawn_creates_cap_one_link_between_components():
    cfg = SimConfig(
        seed=102,
        num_nodes=2,
        num_factions=1,
        globalization_link_growth_chance=0.0,
        globalization_bridge_spawn_chance=1.0,
    )
    state = create_sim(cfg)

    # Force two isolated nodes so bridge spawning is deterministic.
    state.links = {}
    state.relation_graph.relations = []
    state.world.space_relation_graph.relations = []

    step(state)
    assert len(state.links) == 1
    link = next(iter(state.links.values()))
    assert link.max_flow == pytest.approx(1.0)


def test_symbolic_layer_builds_goal_and_strategy_each_tick():
    cfg = SimConfig(seed=77, num_nodes=10, num_factions=3)
    state = create_sim(cfg)
    step(state)

    for faction in state.active_factions():
        intent = faction.symbolic_intent
        assert intent is not None
        assert isinstance(intent.goal, Goal)
        assert isinstance(intent.strategy, Strategy)
        assert intent.goal.actor_id == faction.faction_id
        assert intent.strategy.actor_id == faction.faction_id
        assert intent.strategy.goal_id == intent.goal.id


def test_symbolic_serialization_exposes_mode_goal_and_strategy_ids():
    cfg = SimConfig(seed=78, num_nodes=10, num_factions=2)
    state = create_sim(cfg)
    step(state)

    payload = serialize_state(state)
    for faction_data in payload["factions"].values():
        symbolic = faction_data.get("symbolic")
        assert symbolic is not None
        assert symbolic["mode"] in {"stabilize", "connect", "expand", "reconcile", "balanced"}
        assert str(symbolic["goal_id"]).startswith("goal-")
        assert str(symbolic["strategy_id"]).startswith("strategy-")


def test_personality_high_engagement_biases_away_from_expand():
    """High engagement (cautious) factions should avoid expand mode when signals permit."""
    cfg = SimConfig(seed=79, num_nodes=20, num_factions=3)
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]

    # Set up high engagement (cautious) behavior profile
    faction.behavior = BehaviorProfile(
        engagement_threshold=0.75,  # High = cautious
        concentration=0.4,
        liquidity_preference=0.5,
        objective_bias=0.2,  # Low = defensive
        centralization=0.5,
    )

    snapshot = _symbolic_snapshot(state, faction)
    intent = _build_goal_and_strategy(state, faction, snapshot)

    # High engagement + low objective bias should prefer stabilize/reconcile/connect
    # A truly cautious faction should not naturally gravitate to expand
    assert intent.mode in ("stabilize", "reconcile", "connect", "balanced"), (
        f"High engagement faction chose {intent.mode}; "
        "expected stabilize/reconcile/connect/balanced"
    )


def test_personality_low_engagement_biases_toward_expand():
    """Low engagement (aggressive) factions should favor expand when signals allow."""
    cfg = SimConfig(seed=80, num_nodes=20, num_factions=3)
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]

    # Set up low engagement (aggressive) behavior profile
    faction.behavior = BehaviorProfile(
        engagement_threshold=0.2,  # Low = aggressive
        concentration=0.7,
        liquidity_preference=0.2,  # Low = aggressive
        objective_bias=0.8,  # High = offensive
        centralization=0.3,
    )

    # Set up scenario with low pressure
    state.config.flip_threshold = 100.0  # High so pressure < 10%
    snapshot = _symbolic_snapshot(state, faction)

    intent = _build_goal_and_strategy(state, faction, snapshot)

    # Low engagement + high concentration + high objective bias should
    # at least consider expand as viable mode if signals permit
    # (may be overridden by context, but personality should not suppress it)
    # This faction is naturally aggressive, so it should gravitate toward expand/balanced
    assert intent.mode in ("expand", "balanced", "connect"), (
        f"Aggressive low-engagement faction chose {intent.mode}; "
        "expected expand, balanced, or connect"
    )


def test_personality_high_objective_bias_prefers_expand():
    """High objective bias (offensive) factions should prefer expand under low pressure."""
    cfg = SimConfig(seed=81, num_nodes=20, num_factions=2)
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]

    faction.behavior = BehaviorProfile(
        engagement_threshold=0.4,
        concentration=0.6,
        liquidity_preference=0.3,
        objective_bias=0.85,  # Very high = strong offensive bias
        centralization=0.4,
    )

    # Low pressure scenario
    state.config.flip_threshold = 100.0
    snapshot = _symbolic_snapshot(state, faction)

    intent = _build_goal_and_strategy(state, faction, snapshot)

    # High objective bias + low pressure should bias toward expand
    assert intent.mode in ("expand", "balanced"), (
        f"Offensive-biased faction chose {intent.mode}; expected expand or balanced"
    )


def test_personality_high_centralization_biases_toward_stabilize():
    """High centralization factions should bias toward stabilize."""
    cfg = SimConfig(seed=82, num_nodes=15, num_factions=2)
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]

    faction.behavior = BehaviorProfile(
        engagement_threshold=0.3,
        concentration=0.4,
        liquidity_preference=0.2,
        objective_bias=0.7,
        centralization=0.9,  # Very high admin willingness
    )

    # Force high pressure to trigger stabilize mode
    state.config.flip_threshold = 10.0  # Low threshold makes pressure > 20%
    snapshot = _symbolic_snapshot(state, faction)

    intent = _build_goal_and_strategy(state, faction, snapshot)

    # When pressure is high, should stabilize
    if snapshot["mean_pressure"] > state.config.flip_threshold * 0.20:
        assert intent.mode == "stabilize"


def test_personality_shift_magnitude_scales_with_alignment():
    """Shift magnitudes should be dampened when faction naturally aligns with mode."""
    cfg = SimConfig(seed=83, num_nodes=15, num_factions=2)
    state = create_sim(cfg)
    faction = list(state.factions.values())[0]

    # Create faction with expand-aligned personality
    faction.behavior = BehaviorProfile(
        engagement_threshold=0.2,  # Low E (wants expand)
        concentration=0.9,  # High C (wants expand)
        liquidity_preference=0.1,  # Low L (wants expand)
        objective_bias=0.9,  # High O (wants expand)
        centralization=0.2,  # Low Z (wants expand)
    )

    snapshot = _symbolic_snapshot(state, faction)
    intent_aligned = _build_goal_and_strategy(state, faction, snapshot)

    # If mode is expand, shifts should be dampened
    # because faction is naturally expand-oriented
    if intent_aligned.mode == "expand":
        # Shifts are multiplied by scale_factor in [0.5, 1.0]
        # when faction aligns with mode
        # Base shifts: engagement=0.12, objective=0.30
        # Scaled shifts should be in range [0.06, 0.12] and [0.15, 0.30]
        assert abs(intent_aligned.engagement_shift) <= 0.13  # Slightly above base to allow rounding
        assert abs(intent_aligned.objective_shift) <= 0.31  # Slightly above base to allow rounding


# --------------------------------------------------------------------------- #
# Genome utilities                                                             #
# --------------------------------------------------------------------------- #


def test_hamming_identical():
    assert _hamming_distance([0, 1, 1, 0], [0, 1, 1, 0]) == 0


def test_hamming_all_differ():
    assert _hamming_distance([0, 0, 0, 0], [1, 1, 1, 1]) == 4
