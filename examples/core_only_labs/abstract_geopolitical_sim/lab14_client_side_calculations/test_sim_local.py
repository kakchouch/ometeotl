"""Tests for Lab 14 — Client-Side Calculations.

Run with:
    python -m pytest -q examples/lab14_client_side_calculations/test_sim_local.py
"""

from __future__ import annotations

import pytest

from examples.core_only_labs.abstract_geopolitical_sim.lab14_client_side_calculations.config import SimConfig
from examples.core_only_labs.abstract_geopolitical_sim.lab14_client_side_calculations.engine import (
    SimState,
    Node,
    Faction,
    BehaviorProfile,
    TechVector,
    Link,
    create_sim,
    step,
    serialize_state,
    _apply_conquest,
    _collect_income,
    _update_devastation,
    _apply_stock_cap,
    _node_effective_stock_cap,
    _node_effective_production,
    _get_perceived_devastation,
    _plan_moves,
    _reset_link_usage,
)
from examples.core_only_labs.abstract_geopolitical_sim.lab14_client_side_calculations.perception import get_faction_perception


# =========================================================================== #
# Config                                                                       #
# =========================================================================== #


def test_config_defaults_valid():
    SimConfig().validate()


def test_devastation_config_bad_values_rejected():
    with pytest.raises(ValueError):
        SimConfig(devastation_window_size=0).validate()
    with pytest.raises(ValueError):
        SimConfig(devastation_flip_increment=1.5).validate()
    with pytest.raises(ValueError):
        SimConfig(devastation_recovery_rate=-0.01).validate()
    with pytest.raises(ValueError):
        SimConfig(devastation_cap_penalty=2.0).validate()
    with pytest.raises(ValueError):
        SimConfig(devastation_production_penalty=-0.1).validate()
    with pytest.raises(ValueError):
        SimConfig(devastation_attractiveness_penalty=1.5).validate()
    with pytest.raises(ValueError):
        SimConfig(base_node_production=-1.0).validate()
    with pytest.raises(ValueError):
        SimConfig(min_stock_cap=-1.0).validate()
    with pytest.raises(ValueError):
        SimConfig(min_node_production=-1.0).validate()


def test_devastation_config_in_to_dict():
    cfg = SimConfig(
        devastation_flip_increment=0.4,
        devastation_recovery_rate=0.02,
        base_node_production=3.0,
        min_stock_cap=2.0,
    )
    d = cfg.to_dict()
    assert d["devastation_flip_increment"] == pytest.approx(0.4)
    assert d["devastation_recovery_rate"] == pytest.approx(0.02)
    assert d["base_node_production"] == pytest.approx(3.0)
    assert d["min_stock_cap"] == pytest.approx(2.0)


# =========================================================================== #
# Invariant 1 — Devastation always in [0, 1]                                  #
# =========================================================================== #


def test_devastation_always_in_range():
    """No node devastation score ever leaves [0, 1] across 25 ticks."""
    cfg = SimConfig(
        seed=1, num_nodes=10, num_factions=3,
        mutation_rate=0.0,
        devastation_flip_increment=0.5,
        devastation_recovery_rate=0.1,
    )
    state = create_sim(cfg)
    for _ in range(25):
        if state.game_over:
            break
        step(state)
        for node in state.nodes.values():
            assert 0.0 <= node.devastation <= 1.0, (
                f"Node {node.node_id} devastation={node.devastation} out of [0,1] "
                f"at tick {state.tick}"
            )


# =========================================================================== #
# Invariant 2 — Devastation only increases on flip ticks                       #
# =========================================================================== #


def test_devastation_increases_only_on_flip():
    """Devastation increases only for nodes that flipped this tick."""
    cfg = SimConfig(
        seed=5, num_nodes=6, num_factions=2,
        devastation_flip_increment=0.4,
        devastation_recovery_rate=0.0,  # disable recovery so only flips move the value
        transport_base_cost=0.0, transport_gas_fee=0.0,
        flip_threshold=1.0, mutation_rate=0.0,
    )
    state = create_sim(cfg)

    neutral_node = next((nid for nid, n in state.nodes.items() if n.owner_id is None), None)
    if neutral_node is None:
        pytest.skip("No neutral node available with this seed")

    devas_before = {nid: n.devastation for nid, n in state.nodes.items()}

    # Trigger a flip by applying pressure past the threshold
    state.nodes[neutral_node].pressure["faction-0"] = 5.0
    state.nodes[neutral_node].pressure_accumulated = 5.0

    flipped = _apply_conquest(state)
    assert neutral_node in flipped, "Expected the neutral node to flip"

    _update_devastation(state, flipped)

    for nid, node in state.nodes.items():
        if node.owner_id is None:
            continue
        if nid in flipped:
            assert node.devastation > devas_before[nid], (
                f"Flipped node {nid}: devastation should have increased "
                f"({devas_before[nid]} → {node.devastation})"
            )
        else:
            assert node.devastation <= devas_before[nid] + 1e-9, (
                f"Stable node {nid}: devastation should not increase on a non-flip tick "
                f"({devas_before[nid]} → {node.devastation})"
            )


# =========================================================================== #
# Invariant 3 — Devastation only decreases on stable ticks                     #
# =========================================================================== #


def test_devastation_decreases_only_on_stable():
    """On a tick with no flips, every owned node's devastation decreases or stays at zero."""
    cfg = SimConfig(
        seed=2, num_nodes=6, num_factions=2,
        devastation_recovery_rate=0.05,
        devastation_flip_increment=0.5,
        flip_threshold=9999.0,  # no flips possible
        mutation_rate=0.0,
    )
    state = create_sim(cfg)
    for node in state.nodes.values():
        if node.owner_id is not None:
            node.devastation = 0.5

    devas_before = {nid: n.devastation for nid, n in state.nodes.items()}
    _update_devastation(state, flipped_ids=[])  # stable tick, zero flips

    for nid, node in state.nodes.items():
        if node.owner_id is None:
            continue
        assert node.devastation <= devas_before[nid] + 1e-9, (
            f"Node {nid}: devastation increased on a stable tick "
            f"({devas_before[nid]} → {node.devastation})"
        )


# =========================================================================== #
# Invariant 4 — Recovery is passive and constant                               #
# =========================================================================== #


def test_devastation_recovery_constant():
    """Each stable tick reduces devastation by exactly DEVASTATION_RECOVERY_RATE."""
    rate = 0.07
    cfg = SimConfig(
        seed=3, num_nodes=4, num_factions=1,
        devastation_recovery_rate=rate,
        mutation_rate=0.0, flip_threshold=9999.0,
    )
    state = create_sim(cfg)

    owned = [nid for nid, n in state.nodes.items() if n.owner_id is not None]
    if not owned:
        pytest.skip("No owned nodes")
    nid = owned[0]
    state.nodes[nid].devastation = 0.5

    before1 = state.nodes[nid].devastation
    _update_devastation(state, [])
    after1 = state.nodes[nid].devastation
    recovery1 = before1 - after1

    before2 = state.nodes[nid].devastation
    _update_devastation(state, [])
    after2 = state.nodes[nid].devastation
    recovery2 = before2 - after2

    assert abs(recovery1 - rate) < 1e-9, f"Tick-1 recovery {recovery1} != rate {rate}"
    assert abs(recovery2 - rate) < 1e-9, f"Tick-2 recovery {recovery2} != rate {rate}"
    assert abs(recovery1 - recovery2) < 1e-9, "Recovery is not constant between ticks"


# =========================================================================== #
# Invariant 5 — Effective stock cap >= MIN_STOCK_CAP                           #
# =========================================================================== #


def test_effective_stock_cap_never_below_min():
    """_node_effective_stock_cap always returns >= min_stock_cap, even at full devastation."""
    cfg = SimConfig(
        seed=1, num_nodes=6, num_factions=2,
        min_stock_cap=3.0,
        devastation_cap_penalty=1.0,  # maximum penalty
        base_stock_cap=10.0, logi_stock_cap_bonus=0.0,
    )
    state = create_sim(cfg)

    for node in state.nodes.values():
        if node.owner_id is None:
            continue
        node.devastation = 1.0  # worst case
        cap = _node_effective_stock_cap(state, node)
        assert cap >= cfg.min_stock_cap - 1e-9, (
            f"Node {node.node_id}: effective_cap={cap:.4f} < min_stock_cap={cfg.min_stock_cap}"
        )


def test_effective_stock_cap_respected_after_full_step():
    """After running the sim 15 ticks, no node's stock exceeds its effective cap."""
    cfg = SimConfig(
        seed=1, num_nodes=6, num_factions=2,
        min_spice_flow=30, max_spice_flow=30,  # flood income
        base_stock_cap=8.0, logi_stock_cap_bonus=0.0,
        min_stock_cap=1.0, devastation_cap_penalty=0.5,
        transport_base_cost=0.0, transport_gas_fee=0.0,
        mutation_rate=0.0, flip_threshold=9999.0,
        cohe_hamming_bonus=0.0, cohe_hamming_decay=0.0,
    )
    state = create_sim(cfg)
    for _ in range(15):
        step(state)

    for node in state.nodes.values():
        if node.owner_id is None or node.owner_id not in state.factions:
            continue
        cap = _node_effective_stock_cap(state, node)
        assert node.spice_stock <= cap + 1e-6, (
            f"Node {node.node_id}: stock={node.spice_stock:.3f} > effective_cap={cap:.3f} "
            f"(devastation={node.devastation:.3f})"
        )


# =========================================================================== #
# Invariant 6 — Effective production >= MIN_NODE_PRODUCTION                    #
# =========================================================================== #


def test_effective_production_never_below_min():
    """_node_effective_production always returns >= min_node_production."""
    cfg = SimConfig(
        seed=1, num_nodes=6, num_factions=2,
        min_node_production=0.5,
        devastation_production_penalty=1.0,  # maximum penalty
        base_node_production=5.0,
    )
    state = create_sim(cfg)

    for node in state.nodes.values():
        node.devastation = 1.0
        prod = _node_effective_production(node, cfg)
        # prod = spice_flow + max(min_node_production, base * (1 - 1*1)) = spice_flow + min
        assert prod >= cfg.min_node_production - 1e-9, (
            f"Node {node.node_id}: effective_production={prod:.4f} < min={cfg.min_node_production}"
        )


# =========================================================================== #
# Invariant 7 — Logi cap and devastation compound multiplicatively             #
# =========================================================================== #


def test_devastation_cap_multiplicative_not_additive():
    """effective_cap = logi_cap * (1 - devas * penalty), NOT logi_cap - devas * penalty."""
    cfg = SimConfig(
        seed=1, num_nodes=6, num_factions=2,
        base_stock_cap=40.0, logi_stock_cap_bonus=10.0,
        devastation_cap_penalty=0.5,
        min_stock_cap=0.0,
    )
    state = create_sim(cfg)

    faction = list(state.factions.values())[0]
    faction.tech = TechVector(diplo=0.0, cohe=0.0, logi=0.5)  # logi_cap = 40 + 0.5*10 = 45.0

    owned = state.nodes_owned_by(faction.faction_id)
    if not owned:
        pytest.skip("No owned nodes")
    node = state.nodes[owned[0]]
    node.devastation = 0.6

    logi_cap = cfg.base_stock_cap + 0.5 * cfg.logi_stock_cap_bonus  # 45.0
    expected_mult = logi_cap * (1.0 - node.devastation * cfg.devastation_cap_penalty)  # 45 * 0.7 = 31.5
    additive_wrong = logi_cap - node.devastation * cfg.devastation_cap_penalty       # 45 - 0.3 = 44.7

    actual = _node_effective_stock_cap(state, node)

    assert abs(actual - expected_mult) < 1e-6, (
        f"Expected multiplicative cap {expected_mult:.4f}, got {actual:.4f}"
    )
    assert abs(actual - additive_wrong) > 1e-2, (
        "Cap appears to be additive instead of multiplicative"
    )


# =========================================================================== #
# Invariant 8 — Ground truth devastation not modified by perception reading    #
# =========================================================================== #


def test_ground_truth_devastation_not_modified_by_perception():
    """Computing perceived devastation for any node must not change node.devastation."""
    cfg = SimConfig(
        seed=7, num_nodes=10, num_factions=3,
        perception_mode="limited",
    )
    state = create_sim(cfg)

    for node in state.nodes.values():
        if node.owner_id is not None:
            node.devastation = 0.4

    devas_before = {nid: n.devastation for nid, n in state.nodes.items()}

    for faction in state.active_factions():
        perception = get_faction_perception(state, faction.faction_id)
        for nid in list(state.nodes.keys()):
            _ = _get_perceived_devastation(state, nid, perception)

    devas_after = {nid: n.devastation for nid, n in state.nodes.items()}
    assert devas_before == devas_after, (
        "Perception reading must not mutate ground-truth node.devastation"
    )


# =========================================================================== #
# Invariant 9 — Planner uses perceived devastation, not ground truth           #
# =========================================================================== #


def test_visible_devastation_reduces_attractiveness():
    """In full mode a visibly devastated target attracts less pressure than a pristine one."""
    cfg = SimConfig(
        seed=100, num_nodes=8, num_factions=2,
        perception_mode="full",
        devastation_attractiveness_penalty=1.0,  # maximum so effect is clear
        base_node_production=10.0,
        transport_base_cost=0.0, transport_gas_fee=0.0,
        mutation_rate=0.0, flip_threshold=9999.0,
    )
    state = create_sim(cfg)
    observer = state.factions["faction-0"]

    border = state.border_targets_for(observer.faction_id)
    if len(border) < 2:
        pytest.skip("Need at least 2 border targets")

    nid_pristine, nid_devastated = border[0], border[1]
    # Equalise flow so the only difference is devastation
    state.nodes[nid_pristine].spice_flow = 5
    state.nodes[nid_devastated].spice_flow = 5
    for key in state.links:
        state.links[key].max_flow = 1000.0
    for nid in state.nodes_owned_by(observer.faction_id):
        state.nodes[nid].spice_stock = 300.0

    observer.behavior.engagement_threshold = 0.0
    observer.behavior.objective_bias = 1.0
    observer.behavior.concentration = 0.0  # target all
    observer.behavior.liquidity_preference = 0.0

    # Pristine vs devastated
    state.nodes[nid_pristine].devastation = 0.0
    state.nodes[nid_devastated].devastation = 1.0

    _plan_moves(state, observer, perception=None)  # full mode

    sent = {nid_pristine: 0.0, nid_devastated: 0.0}
    for src, dst, amt in observer.move_orders:
        if dst in sent:
            sent[dst] += amt

    assert sent[nid_pristine] >= sent[nid_devastated], (
        f"Pristine ({sent[nid_pristine]:.2f}) should attract >= pressure "
        f"than devastated ({sent[nid_devastated]:.2f})"
    )


def test_unperceived_devastation_does_not_affect_planning():
    """In limited mode, devastation of an unperceived node does not change move orders."""
    cfg = SimConfig(
        seed=7, num_nodes=10, num_factions=3,
        perception_mode="limited",
        devastation_attractiveness_penalty=1.0,
        transport_base_cost=0.0, transport_gas_fee=0.0,
        mutation_rate=0.0, flip_threshold=9999.0,
    )
    state = create_sim(cfg)
    observer = list(state.active_factions())[0]
    perception = get_faction_perception(state, observer.faction_id)

    # Nodes that are not visible to the observer and not owned by it
    unperceived_enemy = [
        nid for nid in state.nodes
        if nid not in perception.perceived_spaces
        and state.nodes[nid].owner_id not in (None, observer.faction_id)
    ]
    if not unperceived_enemy:
        pytest.skip("All enemy nodes are perceived in this topology")

    target = unperceived_enemy[0]
    for nid in state.nodes_owned_by(observer.faction_id):
        state.nodes[nid].spice_stock = 100.0
    for key in state.links:
        state.links[key].max_flow = 1000.0

    state.nodes[target].devastation = 0.0
    _plan_moves(state, observer, perception)
    orders_pristine = [(s, d, round(a, 4)) for s, d, a in observer.move_orders]

    state.nodes[target].devastation = 1.0
    _plan_moves(state, observer, perception)
    orders_devastated = [(s, d, round(a, 4)) for s, d, a in observer.move_orders]

    assert orders_pristine == orders_devastated, (
        "Unperceived node devastation must not change planning output"
    )


# =========================================================================== #
# Invariant 10 — Unknown devastation uses neutral modifier (returns None)      #
# =========================================================================== #


def test_get_perceived_devastation_returns_none_for_unperceived():
    """_get_perceived_devastation returns None for nodes outside perception range."""
    cfg = SimConfig(
        seed=7, num_nodes=10, num_factions=3, perception_mode="limited",
    )
    state = create_sim(cfg)
    observer = list(state.active_factions())[0]
    perception = get_faction_perception(state, observer.faction_id)

    unperceived = [nid for nid in state.nodes if nid not in perception.perceived_spaces]
    if not unperceived:
        pytest.skip("All nodes perceived in this topology")

    for nid in unperceived[:5]:
        result = _get_perceived_devastation(state, nid, perception)
        assert result is None, (
            f"Node {nid} is outside perception — "
            f"_get_perceived_devastation must return None, got {result}"
        )


def test_get_perceived_devastation_returns_value_for_perceived():
    """_get_perceived_devastation returns ground truth for nodes within perception range."""
    cfg = SimConfig(
        seed=7, num_nodes=10, num_factions=3, perception_mode="limited",
    )
    state = create_sim(cfg)
    observer = list(state.active_factions())[0]
    perception = get_faction_perception(state, observer.faction_id)

    visible = list(perception.perceived_spaces.keys())
    if not visible:
        pytest.skip("No visible nodes")

    nid = visible[0]
    state.nodes[nid].devastation = 0.42
    result = _get_perceived_devastation(state, nid, perception)
    assert result is not None
    assert abs(result - 0.42) < 1e-9, f"Expected 0.42, got {result}"


def test_full_mode_perceived_devastation_equals_ground_truth():
    """In full mode (perception=None), _get_perceived_devastation returns ground truth."""
    cfg = SimConfig(seed=1, num_nodes=6, num_factions=2, perception_mode="full")
    state = create_sim(cfg)
    nid = list(state.nodes.keys())[0]
    state.nodes[nid].devastation = 0.77

    result = _get_perceived_devastation(state, nid, perception=None)
    assert result is not None
    assert abs(result - 0.77) < 1e-9


# =========================================================================== #
# Audit serialization                                                          #
# =========================================================================== #


def test_serialize_raw_fields_only():
    """Lab 14: raw serialization includes devastation + flip_tick_history but NOT client-computed fields."""
    cfg = SimConfig(seed=1, num_nodes=6, num_factions=2)
    state = create_sim(cfg)
    step(state)
    d = serialize_state(state)
    for node_data in d["nodes"]:
        nid = node_data["node_id"]
        assert "devastation" in node_data, f"Missing 'devastation' for node {nid}"
        assert "flip_tick_history" in node_data, f"Missing 'flip_tick_history' for node {nid}"
        assert isinstance(node_data["flip_tick_history"], list)
        assert 0.0 <= node_data["devastation"] <= 1.0
        # These are now client-computed, must NOT appear in the server payload
        assert "effective_stock_cap" not in node_data, f"Unexpected 'effective_stock_cap' for {nid}"
        assert "effective_production" not in node_data, f"Unexpected 'effective_production' for {nid}"
        assert "flip_count_in_window" not in node_data, f"Unexpected 'flip_count_in_window' for {nid}"
        assert "color" not in node_data, f"Unexpected 'color' for {nid}"
    for fid, faction_data in d["factions"].items():
        assert "total_spice" not in faction_data, f"Unexpected 'total_spice' for {fid}"
        assert "spice_income" not in faction_data, f"Unexpected 'spice_income' for {fid}"
        assert "node_count" not in faction_data, f"Unexpected 'node_count' for {fid}"
        assert "perceived_relations" not in faction_data, f"Unexpected 'perceived_relations' for {fid}"


# =========================================================================== #
# Integration                                                                  #
# =========================================================================== #


def test_multi_step_with_devastation_no_error():
    """Full sim with devastation runs 30 ticks without crashing."""
    cfg = SimConfig(
        seed=42, num_nodes=10, num_factions=3,
        perception_mode="limited",
        devastation_flip_increment=0.3,
        devastation_recovery_rate=0.02,
        devastation_cap_penalty=0.5,
        devastation_production_penalty=0.4,
        base_node_production=3.0,
    )
    state = create_sim(cfg)
    for _ in range(30):
        if state.game_over:
            break
        step(state)
    assert state.tick >= 1


def test_devastation_decays_to_zero_with_no_flips():
    """If no flips occur, devastation eventually reaches 0 for all nodes."""
    cfg = SimConfig(
        seed=3, num_nodes=4, num_factions=1,  # single faction, no conquest possible
        devastation_recovery_rate=0.1,
        mutation_rate=0.0, flip_threshold=9999.0,
    )
    state = create_sim(cfg)
    for node in state.nodes.values():
        if node.owner_id is not None:
            node.devastation = 0.8

    # Run enough stable ticks: 0.8 / 0.1 = 8 ticks needed
    for _ in range(12):
        _update_devastation(state, [])

    for node in state.nodes.values():
        if node.owner_id is None:
            continue
        assert node.devastation < 1e-9, (
            f"Node {node.node_id}: devastation {node.devastation} should reach 0"
        )


def test_devastation_caps_at_one_with_repeated_flips():
    """Repeated flip increments cannot push devastation above 1.0."""
    cfg = SimConfig(
        seed=5, num_nodes=6, num_factions=2,
        devastation_flip_increment=0.4,
        devastation_recovery_rate=0.0,
        flip_threshold=1.0, mutation_rate=0.0,
        transport_base_cost=0.0, transport_gas_fee=0.0,
    )
    state = create_sim(cfg)
    neutral = next((nid for nid, n in state.nodes.items() if n.owner_id is None), None)
    if neutral is None:
        pytest.skip("No neutral node")

    # Force repeated flips on the same node
    for _ in range(10):
        state.nodes[neutral].pressure["faction-0"] = 5.0
        state.nodes[neutral].pressure_accumulated = 5.0
        flipped = _apply_conquest(state)
        _update_devastation(state, flipped)
        # Reset for next iteration
        state.nodes[neutral].pressure = {}
        state.nodes[neutral].pressure_accumulated = 0.0

    assert state.nodes[neutral].devastation <= 1.0 + 1e-9


def test_neutral_nodes_not_devastated():
    """Neutral nodes (owner_id=None) must not accumulate devastation."""
    cfg = SimConfig(
        seed=5, num_nodes=6, num_factions=2,
        devastation_flip_increment=0.5, devastation_recovery_rate=0.0,
        mutation_rate=0.0,
    )
    state = create_sim(cfg)

    # Repeatedly call _update_devastation with an empty flip list
    for _ in range(5):
        _update_devastation(state, [])

    for nid, node in state.nodes.items():
        if node.owner_id is None:
            assert node.devastation == 0.0, (
                f"Neutral node {nid} should never accumulate devastation"
            )
