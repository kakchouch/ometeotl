"""Tests for Lab 6 — Vassal multi-agent simulation.

These tests live in examples and are NOT part of the tracked tests/ tree.
Run with:
    python -m pytest -q examples/lab6_vassal_sim/test_sim_local.py
"""

from __future__ import annotations

import pytest

from examples.core_only_labs.abstract_geopolitical_sim.lab6_vassal_sim.config import SimConfig
from examples.core_only_labs.abstract_geopolitical_sim.lab6_vassal_sim.graph_gen import build_graph, bfs_distances
from examples.core_only_labs.abstract_geopolitical_sim.lab6_vassal_sim.engine import (
    SimState,
    Node,
    Link,
    Faction,
    create_sim,
    step,
    serialize_state,
    _execute_transport,
    _plan_moves,
    _reset_link_usage,
    _collect_income,
    _hamming_distance,
    _random_genome,
    _mutate_genome,
    _mutate_and_check_secession,
    _apply_vassal_tribute,
)
from examples.core_only_labs.abstract_geopolitical_sim.lab6_vassal_sim.perception import (
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


def test_behavior_ranges_are_validated():
    with pytest.raises(ValueError):
        SimConfig(behavior_engagement_min=0.9, behavior_engagement_max=0.1).validate()
    with pytest.raises(ValueError):
        SimConfig(behavior_concentration_min=-0.1).validate()
    with pytest.raises(ValueError):
        SimConfig(behavior_liquidity_max=1.1).validate()


def test_create_sim_assigns_behavior_per_faction():
    cfg = SimConfig(seed=4, num_nodes=8, num_factions=3)
    state = create_sim(cfg)
    for faction in state.factions.values():
        b = faction.behavior
        assert (
            cfg.behavior_engagement_min
            <= b.engagement_threshold
            <= cfg.behavior_engagement_max
        )
        assert (
            cfg.behavior_concentration_min
            <= b.concentration
            <= cfg.behavior_concentration_max
        )
        assert (
            cfg.behavior_liquidity_min
            <= b.liquidity_preference
            <= cfg.behavior_liquidity_max
        )
        assert (
            cfg.behavior_objective_min <= b.objective_bias <= cfg.behavior_objective_max
        )


def test_genetic_drift_also_changes_behavior_values():
    """With high mutation pressure, at least one behavior axis should drift."""
    cfg = SimConfig(
        seed=11,
        num_nodes=10,
        num_factions=2,
        mutation_rate=1.0,
        max_ticks=0,
        behavior_engagement_min=0.5,
        behavior_engagement_max=0.5,
        behavior_concentration_min=0.5,
        behavior_concentration_max=0.5,
        behavior_liquidity_min=0.5,
        behavior_liquidity_max=0.5,
        behavior_objective_min=0.5,
        behavior_objective_max=0.5,
    )
    state = create_sim(cfg)

    fid = sorted(state.factions.keys())[0]
    b0 = state.factions[fid].behavior
    start = (
        b0.engagement_threshold,
        b0.concentration,
        b0.liquidity_preference,
        b0.objective_bias,
    )

    for _ in range(3):
        step(state)

    b1 = state.factions[fid].behavior
    end = (
        b1.engagement_threshold,
        b1.concentration,
        b1.liquidity_preference,
        b1.objective_bias,
    )
    assert end != start, "Expected behavior axes to drift over ticks"


# --------------------------------------------------------------------------- #
# Graph generation                                                             #
# --------------------------------------------------------------------------- #


def test_graph_connectivity():
    cfg = SimConfig(num_nodes=12, seed=7)
    g = build_graph(cfg)
    assert len(g.nodes) == 12
    dists = bfs_distances(g, "node-0")
    unreachable = [nid for nid, d in dists.items() if d < 0]
    assert unreachable == [], f"Unreachable nodes: {unreachable}"


def test_geography_preset_validation():
    with pytest.raises(ValueError):
        SimConfig(geography_preset="invalid").validate()
    SimConfig(geography_preset="pangea").validate()
    SimConfig(geography_preset="continents").validate()
    SimConfig(geography_preset="archipelago").validate()


def test_geography_presets_produce_distinct_topologies():
    """With same seed/size, presets should not collapse to identical edge sets."""
    cfg_base = dict(seed=42, num_nodes=24, graph_mode="geographic")
    g_pangea = build_graph(SimConfig(**cfg_base, geography_preset="pangea"))
    g_cont = build_graph(SimConfig(**cfg_base, geography_preset="continents"))
    g_arch = build_graph(SimConfig(**cfg_base, geography_preset="archipelago"))

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
    """Faction has no spice_stock attribute (removed in Lab 6 model)."""
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

    from examples.core_only_labs.abstract_geopolitical_sim.lab6_vassal_sim.engine import _apply_conquest

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


# --------------------------------------------------------------------------- #
# Genome utilities                                                             #
# --------------------------------------------------------------------------- #


def test_hamming_identical():
    assert _hamming_distance([0, 1, 1, 0], [0, 1, 1, 0]) == 0


def test_hamming_all_differ():
    assert _hamming_distance([0, 0, 0, 0], [1, 1, 1, 1]) == 4


# --------------------------------------------------------------------------- #
# Vassal hierarchy                                                             #
# --------------------------------------------------------------------------- #


def test_autonomy_creates_vassal_with_lineage_metadata():
    cfg = SimConfig(
        seed=13,
        num_nodes=8,
        num_factions=1,
        genome_length=8,
        mutation_rate=0.0,
        drift_threshold_fraction=0.25,
        top_secession_threshold_fraction=0.9,
    )
    state = create_sim(cfg)

    root_id = "faction-0"
    root = state.factions[root_id]
    candidate = next(nid for nid, node in state.nodes.items() if nid != root.capital_id)
    state.nodes[candidate].owner_id = root_id
    state.nodes[candidate].genome = [1, 1, 0, 0, 0, 0, 0, 0]
    root.genome = [0, 0, 0, 0, 0, 0, 0, 0]

    created = _mutate_and_check_secession(state)

    assert created, "Expected at least one new faction"
    new_id = created[0]
    assert new_id.startswith("faction-0.v")
    assert state.factions[new_id].parent_faction_id == root_id
    assert state.factions[new_id].top_ancestor_id == root_id
    assert state.factions[new_id].hierarchy_depth == 1


def test_top_threshold_triggers_independent_secession():
    cfg = SimConfig(
        seed=14,
        num_nodes=8,
        num_factions=1,
        genome_length=8,
        mutation_rate=0.0,
        drift_threshold_fraction=0.25,
        top_secession_threshold_fraction=0.75,
    )
    state = create_sim(cfg)

    root_id = "faction-0"
    root = state.factions[root_id]
    candidate = next(nid for nid, node in state.nodes.items() if nid != root.capital_id)
    state.nodes[candidate].owner_id = root_id
    state.nodes[candidate].genome = [1, 1, 1, 1, 1, 1, 1, 0]
    root.genome = [0, 0, 0, 0, 0, 0, 0, 0]

    created = _mutate_and_check_secession(state)

    assert created, "Expected at least one new faction"
    new_id = created[0]
    assert not new_id.startswith("faction-0.v")
    assert state.factions[new_id].parent_faction_id is None
    assert state.factions[new_id].top_ancestor_id == new_id


def test_vassal_tribute_moves_spice_to_parent_capital():
    cfg = SimConfig(
        seed=15,
        num_nodes=8,
        num_factions=1,
        genome_length=8,
        mutation_rate=0.0,
        drift_threshold_fraction=0.25,
        top_secession_threshold_fraction=0.9,
        vassal_tribute_fraction=0.2,
    )
    state = create_sim(cfg)

    root_id = "faction-0"
    root = state.factions[root_id]
    candidate = next(nid for nid, node in state.nodes.items() if nid != root.capital_id)
    state.nodes[candidate].owner_id = root_id
    state.nodes[candidate].genome = [1, 1, 0, 0, 0, 0, 0, 0]
    root.genome = [0, 0, 0, 0, 0, 0, 0, 0]
    created = _mutate_and_check_secession(state)
    vassal_id = created[0]

    vassal_cap = state.factions[vassal_id].capital_id
    parent_cap = state.factions[root_id].capital_id
    state.nodes[vassal_cap].spice_stock = 50.0
    state.nodes[parent_cap].spice_stock = 0.0

    _apply_vassal_tribute(state)

    assert state.nodes[vassal_cap].spice_stock == pytest.approx(40.0)
    assert state.nodes[parent_cap].spice_stock == pytest.approx(10.0)


def test_serialize_exposes_hierarchy_fields():
    cfg = SimConfig(seed=16, num_nodes=8, num_factions=1)
    state = create_sim(cfg)
    data = serialize_state(state)

    faction_data = data["factions"]["faction-0"]
    assert "parent_faction_id" in faction_data
    assert "top_ancestor_id" in faction_data
    assert "hierarchy_depth" in faction_data
    assert "is_vassal" in faction_data
