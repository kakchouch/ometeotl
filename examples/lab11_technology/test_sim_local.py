"""Tests for Lab 11 — Technology multi-agent simulation.

These tests live in examples and are NOT part of the tracked tests/ tree.
Run with:
    python -m pytest -q examples/lab11_technology/test_sim_local.py
"""

from __future__ import annotations

import pytest
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.strategies import Strategy

from examples.lab11_technology.config import SimConfig
from examples.lab11_technology.graph_gen import build_graph, bfs_distances
from examples.lab11_technology.engine import (
    SimState,
    Node,
    Link,
    Faction,
    BehaviorProfile,
    TechVector,
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
    _compute_tech_investment,
    _compute_tech_investment_debug,
    _extract_tech_signals,
    _compute_tech_alpha,
    _magnitude_3d,
    _apply_stock_cap,
    _compute_hamming_threshold,
    _get_perceived_relation,
    _relation_pressure_factor,
    _mutate_and_check_secession,
)
from examples.lab11_technology.perception import (
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
    from examples.lab11_technology.engine import _genome_to_ecloz

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
    from examples.lab11_technology.engine import _genome_to_ecloz

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
    assert unreachable, "Expected at least one disconnected node in Lab 11 geographic mode"


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

    from examples.lab11_technology.engine import _apply_conquest

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


# --------------------------------------------------------------------------- #
# Lab 11 — Technology invariant tests                                          #
# --------------------------------------------------------------------------- #


def test_ecloz_invariant_during_tick():
    """Invariant 1: ECLOZ axes must not change by more than 0.001 during a tick."""
    cfg = SimConfig(
        seed=42, num_nodes=8, num_factions=3,
        mutation_rate=0.0, drift_threshold_fraction=0.99,
    )
    state = create_sim(cfg)
    for _ in range(5):
        if state.game_over:
            break
        ecloz_before = {
            fid: (
                f.behavior.engagement_threshold,
                f.behavior.concentration,
                f.behavior.liquidity_preference,
                f.behavior.objective_bias,
                f.behavior.centralization,
            )
            for fid, f in state.factions.items()
        }
        step(state)
        for fid, before in ecloz_before.items():
            if fid not in state.factions:
                continue
            f = state.factions[fid]
            after = (
                f.behavior.engagement_threshold,
                f.behavior.concentration,
                f.behavior.liquidity_preference,
                f.behavior.objective_bias,
                f.behavior.centralization,
            )
            for i, (a, b) in enumerate(zip(before, after)):
                assert abs(a - b) < 0.001, (
                    f"ECLOZ axis {i} changed for {fid}: {a} → {b}"
                )


def test_pipeline_does_not_modify_ecloz_genome_relations():
    """Invariants 2 & 5: pipeline is strictly read-only w.r.t. ECLOZ, genome, relations."""
    cfg = SimConfig(seed=7, num_nodes=8, num_factions=2, mutation_rate=0.0)
    state = create_sim(cfg)

    fid = sorted(state.factions.keys())[0]
    faction = state.factions[fid]
    perception = (
        get_faction_perception(state, fid)
        if cfg.perception_mode == "limited"
        else None
    )

    ecloz_before = (
        faction.behavior.engagement_threshold,
        faction.behavior.concentration,
        faction.behavior.liquidity_preference,
        faction.behavior.objective_bias,
        faction.behavior.centralization,
    )
    genome_before = faction.genome[:]
    relations_before = dict(state.relations)

    _compute_tech_investment(state, faction, perception)

    ecloz_after = (
        faction.behavior.engagement_threshold,
        faction.behavior.concentration,
        faction.behavior.liquidity_preference,
        faction.behavior.objective_bias,
        faction.behavior.centralization,
    )
    assert ecloz_before == ecloz_after, "Pipeline modified ECLOZ"
    assert faction.genome == genome_before, "Pipeline modified faction genome"
    assert state.relations == relations_before, "Pipeline modified relation graph"


def test_pipeline_output_not_in_history_before_next_tick():
    """Invariant 3: tech_pending (current tick output) is never in history mid-tick."""
    cfg = SimConfig(seed=42, num_nodes=8, num_factions=2, mutation_rate=0.0)
    state = create_sim(cfg)
    step(state)
    for faction in state.factions.values():
        if faction.is_eliminated:
            continue
        pending = faction.tech_pending
        for hist_vec in faction.tech_investment_history:
            assert hist_vec is not pending, (
                f"tech_pending found in history for {faction.faction_id} — "
                "history must only contain previous ticks"
            )


def test_z_inertia_history_bounded_by_window():
    """Invariant 3: rolling history never exceeds tech_rnd_history_window entries."""
    cfg = SimConfig(seed=42, num_nodes=8, num_factions=2, mutation_rate=0.0)
    state = create_sim(cfg)
    window = state.config.tech_rnd_history_window
    for _ in range(window + 5):
        if state.game_over:
            break
        step(state)
    for faction in state.factions.values():
        assert len(faction.tech_investment_history) <= window, (
            f"History len {len(faction.tech_investment_history)} > window {window}"
        )


def test_truncation_preserves_direction():
    """Invariant 4: economic truncation (step 7) is scalar — angle between v5 and v6 < 0.001 rad."""
    import math

    cfg = SimConfig(
        seed=5, num_nodes=6, num_factions=2, mutation_rate=0.0,
        initial_node_spice=0.001, tech_rnd_base_cost=1000.0,
    )
    state = create_sim(cfg)
    fid = sorted(state.factions.keys())[0]
    faction = state.factions[fid]
    perception = (
        get_faction_perception(state, fid)
        if cfg.perception_mode == "limited"
        else None
    )

    v6, v5 = _compute_tech_investment_debug(state, faction, perception)

    mag5 = _magnitude_3d(v5.diplo, v5.cohe, v5.logi)
    mag6 = _magnitude_3d(v6.diplo, v6.cohe, v6.logi)

    if mag5 > 1e-12 and mag6 > 1e-12:
        dot = v5.diplo * v6.diplo + v5.cohe * v6.cohe + v5.logi * v6.logi
        cos_angle = max(-1.0, min(1.0, dot / (mag5 * mag6)))
        angle = math.acos(cos_angle)
        assert angle < 0.001, (
            f"Direction changed after truncation: angle = {angle:.6f} rad (must be < 0.001)"
        )


def test_tech_levels_only_increase():
    """Tech decay not implemented: tech levels are non-decreasing tick-to-tick."""
    cfg = SimConfig(seed=42, num_nodes=10, num_factions=2, mutation_rate=0.0)
    state = create_sim(cfg)
    prev = {
        fid: TechVector(f.tech.diplo, f.tech.cohe, f.tech.logi)
        for fid, f in state.factions.items()
    }
    for _ in range(10):
        if state.game_over:
            break
        step(state)
        for fid, faction in state.factions.items():
            p = prev.get(fid, TechVector())
            assert faction.tech.diplo >= p.diplo - 1e-9, f"diplo decreased for {fid}"
            assert faction.tech.cohe >= p.cohe - 1e-9, f"cohe decreased for {fid}"
            assert faction.tech.logi >= p.logi - 1e-9, f"logi decreased for {fid}"
            prev[fid] = TechVector(faction.tech.diplo, faction.tech.cohe, faction.tech.logi)


def test_serialize_includes_tech_audit():
    """Audit payload: serialize_state must include tech, tech_investment, tech_alpha."""
    cfg = SimConfig(seed=42, num_nodes=8, num_factions=2, mutation_rate=0.0)
    state = create_sim(cfg)
    step(state)
    payload = serialize_state(state)
    for fid, faction_data in payload["factions"].items():
        assert "tech" in faction_data, f"Missing 'tech' for faction {fid}"
        assert "tech_investment" in faction_data, f"Missing 'tech_investment' for {fid}"
        assert "tech_alpha" in faction_data, f"Missing 'tech_alpha' for {fid}"
        for axis in ("diplo", "cohe", "logi"):
            assert axis in faction_data["tech"], f"tech missing axis {axis}"
            assert axis in faction_data["tech_investment"], f"tech_investment missing axis {axis}"
            assert axis in faction_data["tech_alpha"], f"tech_alpha missing axis {axis}"


def test_v0_deterministic_given_seed():
    """Step 1 die roll is commanded by config seed: same seed → same tech evolution."""
    cfg = SimConfig(seed=99, num_nodes=6, num_factions=2, mutation_rate=0.0)
    state_a = create_sim(cfg)
    state_b = create_sim(cfg)
    for _ in range(5):
        if state_a.game_over or state_b.game_over:
            break
        step(state_a)
        step(state_b)
    for fid in state_a.factions:
        if fid not in state_b.factions:
            continue
        fa, fb = state_a.factions[fid], state_b.factions[fid]
        assert fa.tech.diplo == pytest.approx(fb.tech.diplo), f"diplo mismatch for {fid}"
        assert fa.tech.cohe == pytest.approx(fb.tech.cohe), f"cohe mismatch for {fid}"
        assert fa.tech.logi == pytest.approx(fb.tech.logi), f"logi mismatch for {fid}"


def test_tech_config_defaults_valid():
    """All new tech config defaults pass validation."""
    SimConfig().validate()


def test_tech_config_bad_values_rejected():
    """Out-of-range tech config values are rejected by validate()."""
    with pytest.raises(ValueError):
        SimConfig(tech_diplo_perception_effect=1.5).validate()
    with pytest.raises(ValueError):
        SimConfig(tech_cohe_threshold_bonus=-0.1).validate()
    with pytest.raises(ValueError):
        SimConfig(tech_logi_cost_reduction=2.0).validate()
    with pytest.raises(ValueError):
        SimConfig(tech_rnd_history_window=0).validate()
    with pytest.raises(ValueError):
        SimConfig(tech_reserve_reference=0.0).validate()
    with pytest.raises(ValueError):
        SimConfig(tech_leader_cost_multiplier=-1.0).validate()


def test_logi_reduces_gas_fee():
    """Logi tech reduces delivered spice loss: high Logi → more arrives than low Logi."""
    cfg = SimConfig(
        seed=3, num_nodes=6, num_factions=2,
        transport_base_cost=0.0, transport_gas_fee=0.5,
        initial_node_spice=50.0,
        tech_logi_cost_reduction=1.0,
    )
    state_lo = create_sim(cfg)
    state_hi = create_sim(cfg)

    faction_lo = list(state_lo.factions.values())[0]
    faction_hi = list(state_hi.factions.values())[0]

    src = faction_lo.capital_id
    dst_lo = state_lo.neighbors_of(src)[0]
    dst_hi = state_hi.neighbors_of(src)[0]

    # Force friendly destination
    state_lo.nodes[dst_lo].owner_id = faction_lo.faction_id
    state_hi.nodes[dst_hi].owner_id = faction_hi.faction_id

    for st, faction, dst in ((state_lo, faction_lo, dst_lo), (state_hi, faction_hi, dst_hi)):
        key = (min(src, dst), max(src, dst))
        st.links[key].max_flow = 1000.0
        st.nodes[src].spice_stock = 20.0
        st.nodes[dst].spice_stock = 0.0
        faction.move_orders = [(src, dst, 10.0)]

    # High Logi faction
    faction_hi.tech = TechVector(diplo=0.0, cohe=0.0, logi=1.0)

    _execute_transport(state_lo)
    _execute_transport(state_hi)

    delivered_lo = state_lo.nodes[dst_lo].spice_stock
    delivered_hi = state_hi.nodes[dst_hi].spice_stock

    assert delivered_hi > delivered_lo, (
        f"High Logi ({delivered_hi:.2f}) should deliver more than low Logi ({delivered_lo:.2f})"
    )


def test_diplo_reduces_attacker_aggression():
    """Diplo inflates perceived relation → reduces attacker's offense multiplier."""
    from examples.lab11_technology.engine import _relation_pressure_factor

    cfg = SimConfig(seed=1, num_nodes=6, num_factions=2, tech_diplo_perception_effect=0.4)
    state = create_sim(cfg)

    fids = list(state.factions.keys())
    attacker_id, defender_id = fids[0], fids[1]
    state.know_each_other(attacker_id, defender_id)
    state.relations[state.relation_key(attacker_id, defender_id)] = 0.3

    factor_no_diplo = _relation_pressure_factor(state, attacker_id, defender_id)

    state.factions[defender_id].tech = TechVector(diplo=1.0, cohe=0.0, logi=0.0)
    factor_with_diplo = _relation_pressure_factor(state, attacker_id, defender_id)

    assert factor_with_diplo < factor_no_diplo, (
        f"Diplo should reduce offense factor: {factor_with_diplo:.3f} vs {factor_no_diplo:.3f}"
    )


def test_cohe_raises_secession_threshold():
    """Cohé tech raises the Hamming threshold, preventing secession that would otherwise occur."""
    cfg = SimConfig(
        seed=10, num_nodes=6, num_factions=1,
        genome_length=16, drift_threshold_fraction=0.5,
        mutation_rate=0.0, transport_base_cost=0.0, transport_gas_fee=0.0,
        tech_cohe_threshold_bonus=1.0,
    )
    state = create_sim(cfg)
    faction = state.factions["faction-0"]

    # Force a neighbor node into the faction with maximum drift
    owned = state.nodes_owned_by("faction-0")
    if len(owned) < 2:
        pytest.skip("Need at least 2 owned nodes for this test")

    drifted_id = [nid for nid in owned if nid != faction.capital_id][0]
    drifted_node = state.nodes[drifted_id]
    # Flip all bits → Hamming = genome_length (100% drift)
    drifted_node.genome = [1 - b for b in faction.genome]

    # Without Cohé: hamming = 16 >= threshold 8 → would secede
    hamming = _hamming_distance(drifted_node.genome, faction.genome)
    base_threshold = cfg.drift_threshold_bits
    assert hamming >= base_threshold, "Test setup: genome should exceed base threshold"

    # With max Cohé: effective threshold = base + round(1.0 * 16 * 1.0) = 24 → no secession
    faction.tech = TechVector(diplo=0.0, cohe=1.0, logi=0.0)

    from examples.lab11_technology.engine import _mutate_and_check_secession
    new_fids = _mutate_and_check_secession(state)

    assert drifted_id not in [
        state.factions[fid].capital_id for fid in new_fids
    ], "Cohé should prevent secession at max level"


# =========================================================================== #
# Change 1 — Logistics: stock cap per node                                     #
# =========================================================================== #


def test_stock_cap_no_node_exceeds_cap():
    """After tick resolution no owned node holds spice above its faction's cap."""
    cfg = SimConfig(
        seed=1, num_nodes=6, num_factions=2,
        base_stock_cap=8.0, logi_stock_cap_bonus=0.0,   # strict cap, logi has no effect
        min_spice_flow=20, max_spice_flow=20,            # flood income so cap is binding
        transport_base_cost=0.0, transport_gas_fee=0.0,
        mutation_rate=0.0, flip_threshold=9999.0,        # no conquests or secessions
        cohe_hamming_bonus=0.0, cohe_hamming_decay=0.0,
    )
    state = create_sim(cfg)
    for _ in range(15):
        step(state)

    for node in state.nodes.values():
        if node.owner_id is None or node.owner_id not in state.factions:
            continue
        faction = state.factions[node.owner_id]
        cap = cfg.base_stock_cap + faction.tech.logi * cfg.logi_stock_cap_bonus
        assert node.spice_stock <= cap + 1e-9, (
            f"Node {node.node_id} stock {node.spice_stock:.3f} exceeds cap {cap:.3f}"
        )


def test_stock_cap_destroys_not_redistributes():
    """Excess spice is silently destroyed: total after capping < total before capping."""
    cfg = SimConfig(
        seed=2, num_nodes=4, num_factions=2,
        base_stock_cap=5.0, logi_stock_cap_bonus=0.0,
        transport_base_cost=0.0, transport_gas_fee=0.0,
    )
    state = create_sim(cfg)

    # Force every owned node far above cap.
    for node in state.nodes.values():
        if node.owner_id is not None:
            node.spice_stock = 1000.0

    total_before = sum(n.spice_stock for n in state.nodes.values())
    _apply_stock_cap(state)
    total_after = sum(n.spice_stock for n in state.nodes.values())

    assert total_after < total_before, "Stock cap must destroy excess, not keep it"
    # No node should exceed cap after the call.
    for node in state.nodes.values():
        if node.owner_id is None or node.owner_id not in state.factions:
            continue
        faction = state.factions[node.owner_id]
        cap = cfg.base_stock_cap + faction.tech.logi * cfg.logi_stock_cap_bonus
        assert node.spice_stock <= cap + 1e-9, (
            f"Node {node.node_id} exceeds cap after _apply_stock_cap"
        )


# =========================================================================== #
# Change 2 — Cohesion: Hamming threshold decay without cohé tech               #
# =========================================================================== #


def test_hamming_threshold_never_below_floor():
    """Effective threshold is always >= min_hamming_threshold regardless of decay."""
    cfg = SimConfig(
        seed=3, num_nodes=8, num_factions=3,
        min_hamming_threshold=3.0,
        cohe_hamming_decay=999.0,    # absurdly large decay to stress the floor
        cohe_hamming_bonus=0.0,
    )
    state = create_sim(cfg)

    # Give all neighbors very high cohé so the decay is maximal.
    for f in state.factions.values():
        f.tech = TechVector(diplo=0.0, cohe=1.0, logi=0.0)

    for faction in state.active_factions():
        # Set observing faction cohé to 0 → maximum gap vs neighbors at 1.0.
        faction.tech = TechVector(diplo=0.0, cohe=0.0, logi=0.0)
        threshold = _compute_hamming_threshold(state, faction, perception=None)
        assert threshold >= cfg.min_hamming_threshold, (
            f"Faction {faction.faction_id}: threshold {threshold} < floor {cfg.min_hamming_threshold}"
        )


def test_hamming_threshold_isolated_faction_no_decay():
    """A faction with no visible neighbors has zero decay term."""
    cfg = SimConfig(
        seed=4, num_nodes=4, num_factions=1,
        cohe_hamming_bonus=4.0, cohe_hamming_decay=10.0, min_hamming_threshold=1.0,
    )
    state = create_sim(cfg)
    faction = state.factions["faction-0"]
    faction.tech = TechVector(diplo=0.0, cohe=0.5, logi=0.0)

    threshold = _compute_hamming_threshold(state, faction, perception=None)
    expected = cfg.drift_threshold_bits + 0.5 * cfg.cohe_hamming_bonus
    assert abs(threshold - expected) < 0.01, (
        f"Isolated faction got {threshold:.4f}, expected {expected:.4f}"
    )


def test_hamming_threshold_respects_perception_not_ground_truth():
    """In limited mode, unseen high-cohé factions do NOT increase decay."""
    cfg = SimConfig(
        seed=7, num_nodes=10, num_factions=3,
        perception_mode="limited",
        cohe_hamming_bonus=0.0,      # neutralise bonus; only test decay direction
        cohe_hamming_decay=5.0,
        min_hamming_threshold=1.0,
        mutation_rate=0.0, flip_threshold=9999.0,
    )
    state = create_sim(cfg)

    observer = list(state.active_factions())[0]
    observer.tech = TechVector(diplo=0.0, cohe=0.0, logi=0.0)   # zero cohé → max decay gap

    perception = get_faction_perception(state, observer.faction_id)

    # Identify which factions the observer CAN see (via perceived_spaces).
    visible_fids = {
        state.nodes[nid].owner_id
        for nid in perception.perceived_spaces.keys()
        if nid in state.nodes
        and state.nodes[nid].owner_id not in (None, observer.faction_id)
    }
    # Identify factions the observer CANNOT see.
    unseen_fids = {
        fid for fid in state.factions
        if fid != observer.faction_id and fid not in visible_fids
    }

    if not unseen_fids:
        pytest.skip("All factions visible in this topology — cannot test perception filter")

    # Set all factions cohé = 0 first, then raise only unseen factions' cohé.
    for f in state.factions.values():
        f.tech = TechVector(diplo=0.0, cohe=0.0, logi=0.0)
    observer.tech = TechVector(diplo=0.0, cohe=0.0, logi=0.0)
    for fid in unseen_fids:
        state.factions[fid].tech = TechVector(diplo=0.0, cohe=1.0, logi=0.0)

    threshold_limited = _compute_hamming_threshold(state, observer, perception)
    threshold_full    = _compute_hamming_threshold(state, observer, perception=None)

    # Ground truth includes unseen high-cohé factions → MORE decay → LOWER threshold.
    # Perception-limited view ignores them → LESS or EQUAL decay → HIGHER or EQUAL threshold.
    assert threshold_limited >= threshold_full - 1e-9, (
        f"Limited perception should not apply decay from unseen factions. "
        f"limited={threshold_limited:.4f} full={threshold_full:.4f}"
    )


# =========================================================================== #
# Change 3 — Diplomacy: relative tech gap drives perceptual bias               #
# =========================================================================== #


def test_diplo_bias_does_not_mutate_true_relation():
    """Reading perceived relation must never modify the ground-truth relation graph."""
    cfg = SimConfig(seed=5, num_nodes=6, num_factions=2, diplo_bias_strength=0.5)
    state = create_sim(cfg)
    fids = list(state.factions.keys())
    a, b = fids[0], fids[1]
    state.know_each_other(a, b)
    key = state.relation_key(a, b)
    state.relations[key] = 0.4

    state.factions[a].tech = TechVector(diplo=1.0, cohe=0.0, logi=0.0)
    state.factions[b].tech = TechVector(diplo=0.0, cohe=0.0, logi=0.0)

    true_before = state.relations[key]
    _ = _get_perceived_relation(state, b, a)
    true_after = state.relations[key]

    assert true_before == true_after, (
        f"_get_perceived_relation mutated ground truth: {true_before} → {true_after}"
    )


def test_diplo_perceived_relation_in_range():
    """perceived_relation is always clamped to [0, 1]."""
    cfg = SimConfig(seed=6, num_nodes=4, num_factions=2, diplo_bias_strength=1.0)
    state = create_sim(cfg)
    fids = list(state.factions.keys())
    a, b = fids[0], fids[1]
    state.know_each_other(a, b)

    for true_val in (0.0, 0.5, 0.9, 1.0):
        state.relations[state.relation_key(a, b)] = true_val
        state.factions[a].tech = TechVector(diplo=1.0, cohe=0.0, logi=0.0)
        state.factions[b].tech = TechVector(diplo=0.0, cohe=0.0, logi=0.0)
        perceived = _get_perceived_relation(state, b, a)
        assert perceived is not None
        assert 0.0 <= perceived <= 1.0, (
            f"perceived_relation({true_val}) = {perceived} is out of [0,1]"
        )


def test_diplo_zero_gap_zero_bias():
    """When diplo_tech(A) == diplo_tech(B) the perceived relation equals the true relation."""
    cfg = SimConfig(seed=8, num_nodes=4, num_factions=2, diplo_bias_strength=0.5)
    state = create_sim(cfg)
    fids = list(state.factions.keys())
    a, b = fids[0], fids[1]
    state.know_each_other(a, b)
    true_val = 0.6
    state.relations[state.relation_key(a, b)] = true_val

    for diplo_level in (0.0, 0.5, 1.0):
        state.factions[a].tech = TechVector(diplo=diplo_level, cohe=0.0, logi=0.0)
        state.factions[b].tech = TechVector(diplo=diplo_level, cohe=0.0, logi=0.0)
        perceived = _get_perceived_relation(state, b, a)
        assert perceived is not None
        assert abs(perceived - true_val) < 1e-9, (
            f"Zero gap (diplo={diplo_level}) should give zero bias, got {perceived}"
        )


def test_diplo_bias_not_from_opponent_faction_object():
    """The bias must be computable without the observer accessing opponent's faction object.

    Verified behaviourally: _get_perceived_relation's result matches the formula
    using only observer's own diplo and the (engine-computed) gap — the observer
    does not need to call state.factions[opponent] to arrive at a correct value.
    We confirm by injecting an observer diplo and checking the formula holds.
    """
    cfg = SimConfig(seed=9, num_nodes=4, num_factions=2, diplo_bias_strength=0.4)
    state = create_sim(cfg)
    fids = list(state.factions.keys())
    a, b = fids[0], fids[1]
    state.know_each_other(a, b)
    true_val = 0.3
    state.relations[state.relation_key(a, b)] = true_val

    target_diplo   = 0.8    # faction a (target)
    observer_diplo = 0.2    # faction b (observer)
    state.factions[a].tech = TechVector(diplo=target_diplo,   cohe=0.0, logi=0.0)
    state.factions[b].tech = TechVector(diplo=observer_diplo, cohe=0.0, logi=0.0)

    perceived = _get_perceived_relation(state, b, a)
    expected  = min(1.0, true_val + 0.4 * max(0.0, target_diplo - observer_diplo))

    assert abs(perceived - expected) < 1e-9, (
        f"perceived={perceived:.4f} does not match formula result={expected:.4f}"
    )
