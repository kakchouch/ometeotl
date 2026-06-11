"""Core simulation engine for Lab 13 — Ometeotl Retro-Fit.

Extends Lab 11 (Technology) with per-node devastation scores that:
  - Increase each time a node changes faction ownership (flip).
  - Decrease passively each tick the node is stable (no flip).
  - Reduce the node's effective stock cap (compounded multiplicatively with Logi tech cap).
  - Reduce the node's effective base production (separate from spice_flow).
  - Reduce the node's attractiveness as a conquest target, using PERCEIVED devastation.

All other mechanics (technology pipeline, perception, globalization, etc.) are
inherited from Lab 11 unchanged.
"""

from __future__ import annotations

from collections import deque
import math
import random
from dataclasses import dataclass, field
from typing import Deque, Optional

from ometeotl_core.model.actions import Action, ResourceEffect
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.strategies import Strategy, StrategyNode
from ometeotl_core.model.resources import Resource
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.spaces import Space
from ometeotl_core.model.space_relations import SpaceRelation, SpaceRelationGraph
from ometeotl_core.model.world import World
from ometeotl_core.model.perception import Perception

from .config import SimConfig
from .graph_gen import RawGraph, build_graph, bfs_distances
from .perception import get_faction_perception, visible_border_targets

# --------------------------------------------------------------------------- #
# Genome utilities (unchanged from Lab 11)                                     #
# --------------------------------------------------------------------------- #


def _random_genome(length: int, rng: random.Random) -> list[int]:
    return [rng.randint(0, 1) for _ in range(length)]


def _hamming_distance(a: list[int], b: list[int]) -> int:
    return sum(x != y for x, y in zip(a, b))


def _mutate_genome(genome: list[int], rng: random.Random) -> list[int]:
    idx = rng.randrange(len(genome))
    new = genome[:]
    new[idx] = 1 - new[idx]
    return new


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _magnitude_3d(x: float, y: float, z: float) -> float:
    return math.sqrt(x * x + y * y + z * z)


def _normalize_3d(x: float, y: float, z: float) -> tuple[float, float, float]:
    mag = _magnitude_3d(x, y, z)
    if mag < 1e-12:
        return (0.0, 0.0, 0.0)
    return (x / mag, y / mag, z / mag)


def _random_unit_sphere_3d(rng: random.Random) -> tuple[float, float, float]:
    while True:
        x = rng.gauss(0.0, 1.0)
        y = rng.gauss(0.0, 1.0)
        z = rng.gauss(0.0, 1.0)
        mag = _magnitude_3d(x, y, z)
        if mag > 1e-12:
            return (abs(x) / mag, abs(y) / mag, abs(z) / mag)


def _genome_to_ecloz(genome: list[int]) -> "BehaviorProfile":
    axes: list[list[int]] = [[], [], [], [], []]
    for i, bit in enumerate(genome):
        axes[i % 5].append(bit)
    vals = [sum(a) / len(a) if a else 0.5 for a in axes]
    return BehaviorProfile(
        engagement_threshold=vals[0],
        concentration=vals[1],
        liquidity_preference=vals[2],
        objective_bias=vals[3],
        centralization=vals[4],
    )


def _apply_centralization(state: "SimState", faction: "Faction", node: "Node") -> int:
    z = max(0.0, min(1.0, faction.behavior.centralization))
    available_budget = state.admin_delivery_budget.get(node.node_id, 0.0)
    if z <= 0.0 or node.spice_stock <= 0.0 or available_budget <= 0.0:
        return 0
    drift_indices = [
        idx
        for idx, (node_bit, faction_bit) in enumerate(zip(node.genome, faction.genome))
        if node_bit != faction_bit
    ]
    if not drift_indices:
        return 0
    target_corrections = max(1, round(z * len(drift_indices)))
    admin_cost = state.config.centralization_admin_cost
    spendable_spice = min(node.spice_stock, available_budget)
    affordable = (
        len(drift_indices) if admin_cost <= 0 else int(spendable_spice // admin_cost)
    )
    corrections = min(len(drift_indices), target_corrections, affordable)
    if corrections <= 0:
        return 0
    for idx in drift_indices[:corrections]:
        node.genome[idx] = faction.genome[idx]
    spent = corrections * admin_cost
    node.spice_stock = max(0.0, node.spice_stock - spent)
    _sync_node_stock_to_resource(state, node)
    state.admin_delivery_budget[node.node_id] = max(0.0, available_budget - spent)
    _record_faction_action(
        state,
        faction.faction_id,
        node.node_id,
        "admin_centralization",
        f"suppressed drift on {node.node_id} by {corrections} bit(s)",
        resource_effects=[
            ResourceEffect(
                resource_id=node.spice_resource_id,
                effect_type="consume",
                quantity=float(spent),
                source_id=node.node_actor_id,
            )
        ],
    )
    state.event_log.append(
        f"[tick {state.tick}] ADMIN: {faction.faction_id} spent {spent:.1f} spice "
        f"to suppress drift on {node.node_id} by {corrections} bit(s)"
    )
    return corrections


# --------------------------------------------------------------------------- #
# Data types                                                                   #
# --------------------------------------------------------------------------- #


class Node(Actor):
    def __init__(
        self,
        node_id: str,
        spice_flow: int,
        x: float,
        y: float,
        owner_id: str | None,
        genome: list[int],
        spice_stock: float = 0.0,
        spice_resource_id: str = "",
    ):
        super().__init__(id=node_id)
        self.kind = "node"
        self.composition_mode = "standalone"
        self.add_role("territory")
        self.spice_flow = spice_flow
        self.x = x
        self.y = y
        self.owner_id = owner_id
        self.genome = genome
        self.spice_stock = spice_stock
        self.pressure: dict[str, float] = {}
        self.pressure_accumulated = 0.0
        self.devastation = 0.0
        self.flip_tick_history: list[int] = []
        self.spice_resource_id = spice_resource_id

    @property
    def node_id(self) -> str:
        return self.id

    @property
    def node_actor_id(self) -> str:
        return self.id


@dataclass
class Link:
    source_id: str
    target_id: str
    max_flow: float
    used_flow: float = 0.0


@dataclass
class BehaviorProfile:
    engagement_threshold: float
    concentration: float
    liquidity_preference: float
    objective_bias: float
    centralization: float


@dataclass
class TechVector:
    diplo: float = 0.0
    cohe: float = 0.0
    logi: float = 0.0


@dataclass
class SymbolicIntent:
    goal: Goal
    strategy: Strategy
    mode: str
    engagement_shift: float = 0.0
    concentration_shift: float = 0.0
    liquidity_shift: float = 0.0
    objective_shift: float = 0.0
    centralization_shift: float = 0.0


class Faction(Actor):
    def __init__(
        self,
        faction_id: str,
        capital_id: str,
        genome: list[int],
        behavior: BehaviorProfile,
        color: str = "#888888",
    ):
        super().__init__(id=faction_id)
        self.kind = "faction"
        self.composition_mode = "composite"
        self.capital_id = capital_id
        self.genome = genome
        self.behavior = behavior
        self.color = color
        self.move_orders: list[tuple[str, str, float]] = []
        self.admin_orders: list[tuple[str, str, float]] = []
        self.symbolic_intent: SymbolicIntent | None = None
        self.is_eliminated = False
        self.children_spawned = 0
        self.effective_hamming_threshold = 0.0
        self.tech = TechVector()
        self.tech_pending = TechVector()
        self.tech_investment_history: list[TechVector] = []
        self.tech_alpha: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.recent_action_ids: list[str] = []

    @property
    def faction_id(self) -> str:
        return self.id

    @property
    def actor_id(self) -> str:
        return self.id


@dataclass
class SimState:
    config: SimConfig
    world: World
    relation_graph: SpaceRelationGraph
    nodes: dict[str, Node]
    factions: dict[str, Faction]
    links: dict[tuple[str, str], Link]
    tick: int = 0
    game_over: bool = False
    winner_id: str | None = None
    event_log: list[str] = field(default_factory=list)
    relations: dict[tuple[str, str], float] = field(default_factory=dict)
    admin_delivery_budget: dict[str, float] = field(default_factory=dict)
    action_sequence: int = 0
    latest_action_ids: list[str] = field(default_factory=list)
    action_retention_limit: int = 400
    action_order: Deque[str] = field(default_factory=deque)
    action_owner_by_id: dict[str, str] = field(default_factory=dict)
    _rng: random.Random = field(default_factory=random.Random, repr=False)

    def neighbors_of(self, node_id: str) -> list[str]:
        return self.relation_graph.neighbors_of(node_id)

    def nodes_owned_by(self, faction_id: str) -> list[str]:
        return [nid for nid, n in self.nodes.items() if n.owner_id == faction_id]

    def border_targets_for(self, faction_id: str) -> list[str]:
        owned = set(self.nodes_owned_by(faction_id))
        targets: set[str] = set()
        for nid in owned:
            for nb in self.neighbors_of(nid):
                if self.nodes[nb].owner_id != faction_id:
                    targets.add(nb)
        return sorted(targets)

    def spice_income_for(self, faction_id: str) -> int:
        return sum(
            self.nodes[nid].spice_flow for nid in self.nodes_owned_by(faction_id)
        )

    def total_spice_for(self, faction_id: str) -> float:
        return sum(
            self.nodes[nid].spice_stock for nid in self.nodes_owned_by(faction_id)
        )

    def link_remaining(self, a: str, b: str) -> float:
        key = (min(a, b), max(a, b))
        lnk = self.links.get(key)
        if lnk is None:
            return 0.0
        return max(0.0, lnk.max_flow - lnk.used_flow)

    def active_factions(self) -> list[Faction]:
        return [f for f in self.factions.values() if not f.is_eliminated]

    def relation_key(self, a: str, b: str) -> tuple[str, str]:
        return (min(a, b), max(a, b))

    def relation_between(self, a: str, b: str) -> float | None:
        if a == b:
            return 1.0
        return self.relations.get(self.relation_key(a, b))

    def know_each_other(self, a: str, b: str) -> None:
        if a == b:
            return
        key = self.relation_key(a, b)
        if key not in self.relations:
            self.relations[key] = self.config.relation_initial

    def adjust_relation(self, a: str, b: str, delta: float) -> None:
        if a == b:
            return
        self.know_each_other(a, b)
        key = self.relation_key(a, b)
        current = self.relations.get(key, self.config.relation_initial)
        self.relations[key] = _clamp01(current + delta)


def _registry_get_actor(state: SimState, actor_id: str) -> Actor | None:
    obj = state.world.model_registry.get(actor_id)
    if isinstance(obj, Actor):
        return obj
    return None


def _registry_get_resource(state: SimState, resource_id: str) -> Resource | None:
    obj = state.world.model_registry.get(resource_id)
    if isinstance(obj, Resource):
        return obj
    return None


def _sync_node_stock_to_resource(state: SimState, node: Node) -> None:
    if not node.spice_resource_id:
        return
    spice_res = _registry_get_resource(state, node.spice_resource_id)
    if spice_res is None:
        return
    spice_res.state["quantity"] = max(0.0, float(node.spice_stock))


def _record_faction_action(
    state: SimState,
    faction_id: str,
    space_id: str,
    action_type: str,
    outcome: str,
    resource_effects: list[ResourceEffect] | None = None,
    state_changes: dict | None = None,
) -> None:
    faction = state.factions.get(faction_id)
    if faction is None:
        return
    actor_id = faction.id
    if _registry_get_actor(state, actor_id) is None:
        return
    action_id = f"action-t{state.tick}-{state.action_sequence}"
    state.action_sequence += 1
    action = Action(
        id=action_id,
        actor_id=actor_id,
        world_id=state.world.id,
        space_id=space_id,
        action_type=action_type,
        resource_effects=list(resource_effects or []),
        outcome_description=outcome,
        state_changes=dict(state_changes or {}),
    )
    state.world.register_object(action)
    actor = _registry_get_actor(state, actor_id)
    if actor is not None:
        actor.add_relation("action", action.id)
    state.action_order.append(action.id)
    state.action_owner_by_id[action.id] = faction_id

    limit = max(100, state.action_retention_limit)
    while len(state.action_order) > limit:
        stale_action_id = state.action_order.popleft()
        stale_owner_id = state.action_owner_by_id.pop(stale_action_id, None)
        if stale_owner_id is not None:
            stale_owner_actor = _registry_get_actor(state, stale_owner_id)
            if stale_owner_actor is not None:
                stale_owner_actor.remove_relation("action", stale_action_id)
            stale_faction = state.factions.get(stale_owner_id)
            if stale_faction is not None and stale_action_id in stale_faction.recent_action_ids:
                stale_faction.recent_action_ids.remove(stale_action_id)
        if stale_action_id in state.latest_action_ids:
            state.latest_action_ids.remove(stale_action_id)
        state.world.unregister_object(stale_action_id)

    faction.recent_action_ids.append(action.id)
    if len(faction.recent_action_ids) > 60:
        faction.recent_action_ids = faction.recent_action_ids[-60:]
    state.latest_action_ids.append(action.id)


def _set_node_owner_links(
    state: SimState,
    node: Node,
    old_owner_id: str | None,
    new_owner_id: str | None,
) -> None:
    node_actor = _registry_get_actor(state, node.id)
    spice_resource = _registry_get_resource(state, node.spice_resource_id)
    if old_owner_id is not None and old_owner_id in state.factions:
        old_actor = _registry_get_actor(state, state.factions[old_owner_id].id)
        if old_actor is not None and node_actor is not None:
            old_actor.remove_component(node_actor.id)
        if old_actor is not None and spice_resource is not None:
            old_actor.remove_relation("resource", spice_resource.id)
            spice_resource.remove_relation("owner", old_actor.id)
            spice_resource.remove_relation("user", old_actor.id)

    if new_owner_id is None or new_owner_id not in state.factions:
        if spice_resource is not None:
            spice_resource.state["owner_id"] = None
        return

    new_actor = _registry_get_actor(state, state.factions[new_owner_id].id)
    if new_actor is not None:
        if new_actor.composition_mode != "composite":
            new_actor.composition_mode = "composite"
        if node_actor is not None:
            new_actor.add_component(node_actor.id)
        if spice_resource is not None:
            new_actor.add_relation("resource", spice_resource.id)
    if spice_resource is not None and new_actor is not None:
        spice_resource.add_relation("owner", new_actor.id)
        spice_resource.add_relation("user", new_actor.id)
        spice_resource.state["owner_id"] = new_owner_id


# --------------------------------------------------------------------------- #
# Colour helpers (unchanged)                                                   #
# --------------------------------------------------------------------------- #


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = l - c / 2.0
    sector = int(h / 60.0) % 6
    r1, g1, b1 = [
        (c, x, 0.0),
        (x, c, 0.0),
        (0.0, c, x),
        (0.0, x, c),
        (x, 0.0, c),
        (c, 0.0, x),
    ][sector]
    r = max(0, min(255, round((r1 + m) * 255)))
    g = max(0, min(255, round((g1 + m) * 255)))
    b = max(0, min(255, round((b1 + m) * 255)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _genome_to_color(genome: list[int]) -> str:
    L = len(genome)
    if L == 0:
        return "#888888"
    cx = sum(genome[i] * math.cos(2.0 * math.pi * i / L) for i in range(L))
    cy = sum(genome[i] * math.sin(2.0 * math.pi * i / L) for i in range(L))
    mag = math.hypot(cx, cy)
    hue = (math.degrees(math.atan2(cy, cx))) % 360.0 if mag > 1e-9 else 0.0
    lum = 0.35 + (sum(genome) / L) * 0.20
    return _hsl_to_hex(hue, 0.75, lum)


# --------------------------------------------------------------------------- #
# BFS helpers (unchanged)                                                      #
# --------------------------------------------------------------------------- #


def _bfs_distances_state(state: SimState, source: str) -> dict[str, int]:
    dist: dict[str, int] = {source: 0}
    queue = [source]
    head = 0
    while head < len(queue):
        current = queue[head]
        head += 1
        for nb in state.neighbors_of(current):
            if nb not in dist:
                dist[nb] = dist[current] + 1
                queue.append(nb)
    for nid in state.nodes:
        if nid not in dist:
            dist[nid] = -1
    return dist


def _bfs_distances_visible(
    state: SimState, source: str, visible_ids: set[str]
) -> dict[str, int]:
    dist: dict[str, int] = {source: 0}
    queue = [source]
    head = 0
    while head < len(queue):
        current = queue[head]
        head += 1
        for nb in state.neighbors_of(current):
            if nb not in dist and nb in visible_ids:
                dist[nb] = dist[current] + 1
                queue.append(nb)
    for nid in visible_ids:
        if nid not in dist:
            dist[nid] = -1
    return dist


# --------------------------------------------------------------------------- #
# Lab 12 — Devastation helpers                                                 #
# --------------------------------------------------------------------------- #


def _node_effective_stock_cap(state: SimState, node: Node) -> float:
    """Logi-based cap * (1 - devastation * penalty), floored at min_stock_cap.

    Compound is multiplicative: devastation degrades the already logi-scaled cap.
    """
    cfg = state.config
    if node.owner_id is None or node.owner_id not in state.factions:
        return max(float(cfg.min_stock_cap), float(cfg.base_stock_cap))
    faction = state.factions[node.owner_id]
    logi_cap = cfg.base_stock_cap + faction.tech.logi * cfg.logi_stock_cap_bonus
    effective = logi_cap * (1.0 - node.devastation * cfg.devastation_cap_penalty)
    return max(float(cfg.min_stock_cap), effective)


def _node_effective_production(
    node: Node,
    config: SimConfig,
    devastation_override: Optional[float] = None,
) -> float:
    """Total production per tick = spice_flow + devastation-degraded base_node_production.

    spice_flow is the node's intrinsic resource richness (not degraded by devastation).
    base_node_production is a global per-tick bonus that devastation degrades.

    devastation_override: use this value instead of node.devastation (for perceived production).
    """
    devas = (
        devastation_override if devastation_override is not None else node.devastation
    )
    base = config.base_node_production * (
        1.0 - devas * config.devastation_production_penalty
    )
    return node.spice_flow + max(float(config.min_node_production), base)


def _get_perceived_devastation(
    state: SimState,
    node_id: str,
    perception: Optional[Perception],
) -> Optional[float]:
    """Return devastation of node_id as seen by the observer.

    Full mode (perception=None): always returns ground truth.
    Limited mode: returns ground truth if node is in perceived_spaces, else None.
    Never mutates node.devastation.
    """
    if perception is None:
        return state.nodes[node_id].devastation
    if node_id in perception.perceived_spaces:
        return state.nodes[node_id].devastation
    return None


def _update_devastation(state: SimState, flipped_ids: list[str]) -> None:
    """Update devastation scores after conquest resolution.

    - Flipped nodes: devastation += flip_increment (clamped to 1.0), tick recorded in history.
    - Stable owned nodes: devastation -= recovery_rate (floored at 0.0).
    - Neutral nodes (owner_id=None): untouched.
    - flip_tick_history is pruned to the rolling window each call.
    """
    cfg = state.config
    flipped_set = set(flipped_ids)
    for nid, node in state.nodes.items():
        if node.owner_id is None:
            continue
        # Prune history outside the window
        node.flip_tick_history = [
            t
            for t in node.flip_tick_history
            if state.tick - t < cfg.devastation_window_size
        ]
        if nid in flipped_set:
            node.devastation = min(
                1.0, node.devastation + cfg.devastation_flip_increment
            )
            node.flip_tick_history.append(state.tick)
        else:
            node.devastation = max(
                0.0, node.devastation - cfg.devastation_recovery_rate
            )


# --------------------------------------------------------------------------- #
# Lab 11 — Diplomacy gap bias (unchanged)                                      #
# --------------------------------------------------------------------------- #


def _get_perceived_relation(
    state: SimState, observer_id: str, target_id: str
) -> Optional[float]:
    true_rel = state.relation_between(observer_id, target_id)
    if true_rel is None:
        return None
    observer_diplo = (
        state.factions[observer_id].tech.diplo if observer_id in state.factions else 0.0
    )
    target_diplo = (
        state.factions[target_id].tech.diplo if target_id in state.factions else 0.0
    )
    gap = max(0.0, target_diplo - observer_diplo)
    return _clamp01(true_rel + state.config.diplo_bias_strength * gap)


def _relation_pressure_factor(
    state: SimState, attacker_id: str, defender_id: str
) -> float:
    rel = _get_perceived_relation(state, attacker_id, defender_id)
    if rel is None:
        return 1.0
    bias = state.config.relation_offense_bias
    return max(0.05, 1.0 + bias * (1.0 - 2.0 * rel))


# --------------------------------------------------------------------------- #
# Symbolic deliberation (unchanged from Lab 11)                                #
# --------------------------------------------------------------------------- #


def _effective_behavior(faction: Faction) -> BehaviorProfile:
    base = faction.behavior
    intent = faction.symbolic_intent
    if intent is None:
        return base
    return BehaviorProfile(
        engagement_threshold=_clamp01(
            base.engagement_threshold + intent.engagement_shift
        ),
        concentration=_clamp01(base.concentration + intent.concentration_shift),
        liquidity_preference=_clamp01(
            base.liquidity_preference + intent.liquidity_shift
        ),
        objective_bias=_clamp01(base.objective_bias + intent.objective_shift),
        centralization=_clamp01(base.centralization + intent.centralization_shift),
    )


def _symbolic_snapshot(
    state: SimState, faction: Faction, perception: Optional[Perception] = None
) -> dict[str, float]:
    owned = state.nodes_owned_by(faction.faction_id)
    if perception is not None:
        visible_ids = set(perception.perceived_spaces.keys())
    else:
        visible_ids = set(state.nodes.keys())
    total_nodes = max(1, len(visible_ids))
    node_share = len(owned) / total_nodes
    total_pressure = sum(state.nodes[nid].pressure_accumulated for nid in owned)
    mean_pressure = total_pressure / max(1, len(owned))
    relation_values: list[float] = []
    if perception is not None:
        visible_faction_ids: set[str] = set()
        for nid in visible_ids:
            owner_id = state.nodes[nid].owner_id
            if owner_id is not None and owner_id != faction.faction_id:
                visible_faction_ids.add(owner_id)
    else:
        visible_faction_ids = set(state.factions.keys()) - {faction.faction_id}
    for other_fid in visible_faction_ids:
        rel = state.relation_between(faction.faction_id, other_fid)
        if rel is not None:
            relation_values.append(rel)
    mean_relation = (
        sum(relation_values) / len(relation_values) if relation_values else 0.5
    )
    disconnected_owned = 0
    if perception is not None:
        perceived_adj: dict[str, list[str]] = {nid: [] for nid in visible_ids}
        for perceived_rel in perception.perceived_relations:
            inner = perceived_rel.relation
            if inner.relation_type == "adjacent_to":
                a, b = inner.source_space_id, inner.target_space_id
                if a in perceived_adj:
                    perceived_adj[a].append(b)
                if b in perceived_adj:
                    perceived_adj[b].append(a)
        seen: set[str] = {faction.capital_id}
        bfs_queue: list[str] = [faction.capital_id]
        bfs_head = 0
        while bfs_head < len(bfs_queue):
            cur = bfs_queue[bfs_head]
            bfs_head += 1
            for nb in perceived_adj.get(cur, []):
                if nb not in seen:
                    seen.add(nb)
                    bfs_queue.append(nb)
        for nid in owned:
            if nid not in seen:
                disconnected_owned += 1
    else:
        bfs = _bfs_distances_state(state, faction.capital_id)
        for nid in owned:
            if bfs.get(nid, -1) < 0:
                disconnected_owned += 1
    disconnected_ratio = disconnected_owned / max(1, len(owned))
    return {
        "node_share": node_share,
        "mean_pressure": mean_pressure,
        "mean_relation": mean_relation,
        "disconnected_ratio": disconnected_ratio,
    }


def _build_goal_and_strategy(
    state: SimState, faction: Faction, snapshot: dict[str, float]
) -> SymbolicIntent:
    fid = faction.faction_id
    tick = state.tick
    pressure = snapshot["mean_pressure"]
    node_share = snapshot["node_share"]
    mean_relation = snapshot["mean_relation"]
    disconnected_ratio = snapshot["disconnected_ratio"]
    behavior = faction.behavior

    if pressure > state.config.flip_threshold * 0.20:
        mode = "stabilize"
        priority = 0.9
    elif disconnected_ratio > 0.15:
        mode = "connect"
        priority = 0.8
    elif node_share < 0.34 and mean_relation < 0.55:
        mode = "expand"
        priority = 0.85
    elif mean_relation > 0.75:
        mode = "reconcile"
        priority = 0.7
    else:
        mode = "balanced"
        priority = 0.65

    if behavior.engagement_threshold > 0.65 and mode in ("expand", "connect"):
        mode = "stabilize"
        priority = 0.8
    elif behavior.engagement_threshold < 0.35 and mode == "reconcile":
        mode = "expand"
        priority = 0.85
    elif behavior.concentration > 0.7 and mode != "expand":
        priority = max(priority, 0.80)
    elif behavior.liquidity_preference > 0.65 and mode == "expand":
        mode = "reconcile"
        priority = 0.75
    elif behavior.objective_bias > 0.7 and mode in ("stabilize", "reconcile"):
        if pressure < state.config.flip_threshold * 0.10:
            mode = "expand"
            priority = 0.80
    elif behavior.centralization < 0.3 and mode == "stabilize":
        mode = "balanced"
        priority = 0.65

    goal = Goal(
        id=f"goal-{fid}-t{tick}",
        actor_id=fid,
        kind="final",
        priority=priority,
        status="active",
        target_condition={
            "mode": mode,
            "node_share": round(node_share, 3),
            "mean_relation": round(mean_relation, 3),
            "mean_pressure": round(pressure, 3),
            "disconnected_ratio": round(disconnected_ratio, 3),
        },
    )
    root_node = StrategyNode(
        node_id=f"strat-root-{fid}-t{tick}", action_id=f"action-{mode}"
    )
    strategy = Strategy(
        id=f"strategy-{fid}-t{tick}",
        actor_id=fid,
        goal_id=goal.id,
        root_node_id=root_node.node_id,
        nodes=[root_node],
        projection_policy="symbolic_rule",
    )

    scale_factor = 1.0
    if mode == "stabilize":
        base_e, base_o, base_c, base_l, base_z = (
            behavior.engagement_threshold,
            behavior.objective_bias,
            behavior.concentration,
            behavior.liquidity_preference,
            behavior.centralization,
        )
        alignment = (1 - base_e) + (1 - base_o) + (1 - base_c) + base_l + base_z
        scale_factor = 1.0 - (alignment / 5.0 * 0.5)
        return SymbolicIntent(
            goal=goal,
            strategy=strategy,
            mode=mode,
            engagement_shift=-0.08 * scale_factor,
            objective_shift=-0.28 * scale_factor,
            concentration_shift=-0.10 * scale_factor,
            liquidity_shift=0.08 * scale_factor,
            centralization_shift=0.24 * scale_factor,
        )
    if mode == "connect":
        base_e, base_o, base_c, base_l, base_z = (
            behavior.engagement_threshold,
            behavior.objective_bias,
            behavior.concentration,
            behavior.liquidity_preference,
            behavior.centralization,
        )
        alignment = (
            (1 - base_e) + (1 - base_o) + (1 - base_c) + (1 - base_l) + (base_z * 0.5)
        )
        scale_factor = 1.0 - (alignment / 4.5 * 0.4)
        return SymbolicIntent(
            goal=goal,
            strategy=strategy,
            mode=mode,
            engagement_shift=-0.02 * scale_factor,
            objective_shift=-0.10 * scale_factor,
            concentration_shift=-0.20 * scale_factor,
            liquidity_shift=-0.04 * scale_factor,
            centralization_shift=0.10 * scale_factor,
        )
    if mode == "expand":
        base_e, base_o, base_c, base_l, base_z = (
            behavior.engagement_threshold,
            behavior.objective_bias,
            behavior.concentration,
            behavior.liquidity_preference,
            behavior.centralization,
        )
        alignment = base_e + base_o + base_c + (1 - base_l) + (1 - base_z)
        scale_factor = 1.0 - (alignment / 5.0 * 0.5)
        return SymbolicIntent(
            goal=goal,
            strategy=strategy,
            mode=mode,
            engagement_shift=0.12 * scale_factor,
            objective_shift=0.30 * scale_factor,
            concentration_shift=0.16 * scale_factor,
            liquidity_shift=-0.10 * scale_factor,
            centralization_shift=-0.10 * scale_factor,
        )
    if mode == "reconcile":
        base_e, base_o, base_c, base_l, base_z = (
            behavior.engagement_threshold,
            behavior.objective_bias,
            behavior.concentration,
            behavior.liquidity_preference,
            behavior.centralization,
        )
        alignment = (1 - base_e) + (base_o * 0.5) + (1 - base_c) + base_l + (1 - base_z)
        scale_factor = 1.0 - (alignment / 4.5 * 0.4)
        return SymbolicIntent(
            goal=goal,
            strategy=strategy,
            mode=mode,
            engagement_shift=-0.10 * scale_factor,
            objective_shift=-0.16 * scale_factor,
            concentration_shift=-0.08 * scale_factor,
            liquidity_shift=0.10 * scale_factor,
            centralization_shift=0.06 * scale_factor,
        )
    return SymbolicIntent(
        goal=goal,
        strategy=strategy,
        mode="balanced",
        engagement_shift=0.0,
        objective_shift=0.0,
        concentration_shift=0.0,
        liquidity_shift=0.0,
        centralization_shift=0.0,
    )


def _run_symbolic_deliberation(
    state: SimState, faction: Faction, perception: Optional[Perception] = None
) -> None:
    snapshot = _symbolic_snapshot(state, faction, perception)
    faction.symbolic_intent = _build_goal_and_strategy(state, faction, snapshot)


def _grow_relations(state: SimState) -> None:
    rate = state.config.relation_growth_rate
    if rate <= 0.0:
        return
    for key, value in list(state.relations.items()):
        state.relations[key] = _clamp01(value + rate)


# --------------------------------------------------------------------------- #
# Logistics AI — route planning (modified for devastation attractiveness)      #
# --------------------------------------------------------------------------- #


def _plan_moves(
    state: SimState,
    faction: Faction,
    perception: Optional[Perception] = None,
) -> None:
    """Plan spice routing with devastation-aware attractiveness scoring.

    offense_score(node) = perceived_production(node) / distance * relation_factor
                          * (1 - perceived_devastation * attractiveness_penalty)

    perceived_production uses perceived devastation (None → neutral modifier 1.0).
    perceived_devastation = None for nodes outside perception range → neutral modifier.
    """
    faction_id = faction.faction_id
    behavior = _effective_behavior(faction)
    owned = set(state.nodes_owned_by(faction_id))
    faction.move_orders = []
    if not owned:
        return

    if perception is not None:
        offense_targets = set(visible_border_targets(perception, owned))
    else:
        offense_targets = set(state.border_targets_for(faction_id))

    defense_targets: dict[str, float] = {}
    for nid in owned:
        node = state.nodes[nid]
        if node.pressure_accumulated > 0:
            defense_targets[nid] = node.pressure_accumulated * (1.0 + node.spice_flow)

    if perception is not None:
        _visible = set(perception.perceived_spaces.keys())
        bfs = _bfs_distances_visible(state, faction.capital_id, _visible)
    else:
        bfs = _bfs_distances_state(state, faction.capital_id)

    cfg = state.config
    offense_scores: dict[str, float] = {}
    for nid in offense_targets:
        d = max(1, bfs.get(nid, 1))
        target_owner = state.nodes[nid].owner_id
        relation_factor = 1.0
        if target_owner is not None and target_owner != faction_id:
            state.know_each_other(faction_id, target_owner)
            relation_factor = _relation_pressure_factor(state, faction_id, target_owner)

        # Lab 12: perceived devastation → attractiveness modifier
        perceived_devas = _get_perceived_devastation(state, nid, perception)
        if perceived_devas is None:
            devas_mod = 1.0  # unknown devastation → neutral modifier
        else:
            devas_mod = 1.0 - perceived_devas * cfg.devastation_attractiveness_penalty
            devas_mod = max(0.0, devas_mod)

        perceived_prod = _node_effective_production(
            state.nodes[nid], cfg, perceived_devas
        )
        offense_scores[nid] = (perceived_prod / d) * relation_factor * devas_mod

    if offense_scores:
        max_off = max(offense_scores.values())
        if max_off > 0:
            for nid in list(offense_scores.keys()):
                normalized = offense_scores[nid] / max_off
                if normalized < behavior.engagement_threshold:
                    offense_scores[nid] = 0.0

    scores: dict[str, float] = {}
    for nid, s in offense_scores.items():
        mixed = behavior.objective_bias * s
        if mixed > 0:
            scores[nid] = scores.get(nid, 0.0) + mixed
    for nid, s in defense_targets.items():
        mixed = (1.0 - behavior.objective_bias) * s
        if mixed > 0:
            scores[nid] = scores.get(nid, 0.0) + mixed

    if not scores:
        return

    ranked_targets = [
        nid
        for nid, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        if score > 0
    ]
    if not ranked_targets:
        return

    target_count = max(1, round((1.0 - behavior.concentration) * len(ranked_targets)))
    selected_targets = ranked_targets[:target_count]

    spend_fraction = state.config.max_spice_move_fraction * (
        1.0 - behavior.liquidity_preference
    )
    spend_fraction = max(0.05, min(1.0, spend_fraction))
    base_cost = state.config.transport_base_cost

    for src_index, src_id in enumerate(sorted(owned)):
        src_node = state.nodes[src_id]
        if src_node.spice_stock <= base_cost:
            continue
        max_dispatch = (src_node.spice_stock - base_cost) * spend_fraction
        target_id = selected_targets[src_index % len(selected_targets)]
        next_hop = _next_hop_toward(state, src_id, target_id, owned, faction_id)
        if next_hop is None:
            continue
        remaining_cap = state.link_remaining(src_id, next_hop)
        if remaining_cap <= 0:
            continue
        amount = min(max_dispatch, remaining_cap)
        if amount <= 0:
            continue
        faction.move_orders.append((src_id, next_hop, amount))


def _plan_centralization(state: SimState, faction: Faction) -> None:
    faction.admin_orders = []
    z = max(0.0, min(1.0, _effective_behavior(faction).centralization))
    if z <= 0.0:
        return
    owned = set(state.nodes_owned_by(faction.faction_id))
    if not owned:
        return
    admin_cost = state.config.centralization_admin_cost
    if admin_cost < 0:
        return
    source_id = faction.capital_id if faction.capital_id in owned else sorted(owned)[0]
    source_stock = state.nodes[source_id].spice_stock
    if source_stock <= state.config.transport_base_cost:
        return
    bfs = _bfs_distances_state(state, source_id)
    drifted_nodes = []
    for nid in owned:
        node = state.nodes[nid]
        drift = _hamming_distance(node.genome, faction.genome)
        if drift <= 0:
            continue
        drifted_nodes.append((drift, nid, bfs.get(nid, -1)))
    drifted_nodes.sort(reverse=True)
    gas_factor = 1.0 - state.config.transport_gas_fee
    if gas_factor <= 0.0:
        return
    for drift, nid, _depth in drifted_nodes:
        target_bits = max(1, round(z * drift))
        desired_receive = target_bits * admin_cost
        if desired_receive <= 0:
            continue
        desired_send = desired_receive / gas_factor
        next_hop = _next_hop_toward(state, source_id, nid, owned, faction.faction_id)
        if next_hop is None:
            continue
        remaining_cap = state.link_remaining(source_id, next_hop)
        if remaining_cap <= 0:
            continue
        amount = min(desired_send, remaining_cap)
        if amount <= 0:
            continue
        faction.admin_orders.append((source_id, next_hop, amount))


def _next_hop_toward(
    state: SimState, src: str, target: str, owned: set[str], faction_id: str
) -> str | None:
    if target in state.neighbors_of(src):
        return target
    dist: dict[str, int] = {src: 0}
    prev: dict[str, str] = {}
    queue = [src]
    head = 0
    while head < len(queue):
        cur = queue[head]
        head += 1
        for nb in state.neighbors_of(cur):
            if nb in dist:
                continue
            if nb not in owned and nb != target:
                continue
            dist[nb] = dist[cur] + 1
            prev[nb] = cur
            queue.append(nb)
    if target not in prev:
        return None
    node = target
    while prev.get(node) != src:
        p = prev.get(node)
        if p is None:
            return None
        node = p
    return node


def _reset_link_usage(state: SimState) -> None:
    for lnk in state.links.values():
        lnk.used_flow = 0.0
    state.admin_delivery_budget = {}


# --------------------------------------------------------------------------- #
# Transport execution (unchanged from Lab 11)                                  #
# --------------------------------------------------------------------------- #


def _execute_transport(state: SimState) -> None:
    base_cost = state.config.transport_base_cost
    gas_fee = state.config.transport_gas_fee

    for faction in state.active_factions():
        effective_gas_fee = max(
            0.0,
            gas_fee * (1.0 - faction.tech.logi * state.config.tech_logi_cost_reduction),
        )
        for src_id, dst_id, amount in faction.move_orders:
            src_node = state.nodes[src_id]
            dst_node = state.nodes[dst_id]
            link_key = (min(src_id, dst_id), max(src_id, dst_id))
            lnk = state.links.get(link_key)
            if lnk is not None:
                cap_available = max(0.0, lnk.max_flow - lnk.used_flow)
                amount = min(amount, cap_available)
                if amount <= 0:
                    continue
                lnk.used_flow += amount
            total_required = base_cost + amount
            if src_node.spice_stock < total_required:
                amount = src_node.spice_stock - base_cost
                if amount <= 0:
                    burned = min(base_cost, src_node.spice_stock)
                    src_node.spice_stock -= burned
                    continue
            src_node.spice_stock -= base_cost
            src_node.spice_stock -= amount
            src_node.spice_stock = max(0.0, src_node.spice_stock)
            _sync_node_stock_to_resource(state, src_node)
            delivered = amount * (1.0 - effective_gas_fee)
            if dst_node.owner_id == faction.faction_id:
                dst_node.spice_stock += delivered
                _sync_node_stock_to_resource(state, dst_node)
                _record_faction_action(
                    state,
                    faction.faction_id,
                    dst_id,
                    "transfer",
                    f"moved {delivered:.1f} spice from {src_id} to {dst_id}",
                    resource_effects=[
                        ResourceEffect(
                            resource_id=src_node.spice_resource_id,
                            effect_type="transfer",
                            quantity=float(delivered),
                            source_id=src_node.node_actor_id,
                            target_id=dst_node.node_actor_id,
                        )
                    ],
                )
            else:
                fid = faction.faction_id
                dst_node.pressure.setdefault(fid, 0.0)
                dst_node.pressure[fid] += delivered
                dst_node.pressure_accumulated += delivered
                defender_id = dst_node.owner_id
                if defender_id is not None and defender_id != fid:
                    delta = -delivered * state.config.relation_pressure_impact
                    state.adjust_relation(fid, defender_id, delta)
                _record_faction_action(
                    state,
                    faction.faction_id,
                    dst_id,
                    "pressure",
                    f"projected {delivered:.1f} pressure from {src_id} to {dst_id}",
                    resource_effects=[
                        ResourceEffect(
                            resource_id=src_node.spice_resource_id,
                            effect_type="transfer",
                            quantity=float(delivered),
                            source_id=src_node.node_actor_id,
                            target_id=dst_node.node_actor_id,
                        )
                    ],
                )
                state.event_log.append(
                    f"[tick {state.tick}] {fid} delivered {delivered:.1f} pressure to"
                    f" {dst_id} (base_cost {base_cost:.1f} + gas {amount-delivered:.1f})"
                )

        for src_id, dst_id, amount in faction.admin_orders:
            src_node = state.nodes[src_id]
            dst_node = state.nodes[dst_id]
            link_key = (min(src_id, dst_id), max(src_id, dst_id))
            lnk = state.links.get(link_key)
            if lnk is not None:
                cap_available = max(0.0, lnk.max_flow - lnk.used_flow)
                amount = min(amount, cap_available)
                if amount <= 0:
                    continue
                lnk.used_flow += amount
            total_required = base_cost + amount
            if src_node.spice_stock < total_required:
                amount = src_node.spice_stock - base_cost
                if amount <= 0:
                    burned = min(base_cost, src_node.spice_stock)
                    src_node.spice_stock -= burned
                    continue
            src_node.spice_stock -= base_cost
            src_node.spice_stock -= amount
            src_node.spice_stock = max(0.0, src_node.spice_stock)
            _sync_node_stock_to_resource(state, src_node)
            delivered = amount * (1.0 - gas_fee)
            dst_node.spice_stock += delivered
            _sync_node_stock_to_resource(state, dst_node)
            state.admin_delivery_budget[dst_id] = (
                state.admin_delivery_budget.get(dst_id, 0.0) + delivered
            )
            _record_faction_action(
                state,
                faction.faction_id,
                dst_id,
                "admin_transfer",
                f"routed {delivered:.1f} admin spice to {dst_id}",
                resource_effects=[
                    ResourceEffect(
                        resource_id=src_node.spice_resource_id,
                        effect_type="transfer",
                        quantity=float(delivered),
                        source_id=src_node.node_actor_id,
                        target_id=dst_node.node_actor_id,
                    )
                ],
            )
            state.event_log.append(
                f"[tick {state.tick}] ADMIN route: {faction.faction_id} delivered "
                f"{delivered:.1f} spice to {dst_id}"
            )


# --------------------------------------------------------------------------- #
# Conquest (returns flipped list — consumed by _update_devastation)            #
# --------------------------------------------------------------------------- #


def _apply_conquest(state: SimState) -> list[str]:
    """Check nodes for ownership flips. Returns list of flipped node_ids."""
    flipped: list[str] = []
    for nid, node in state.nodes.items():
        if node.pressure_accumulated < state.config.flip_threshold:
            continue
        if not node.pressure:
            continue
        conqueror_id = max(node.pressure, key=lambda fid: node.pressure[fid])
        old_owner = node.owner_id
        if old_owner == conqueror_id:
            node.pressure_accumulated = 0.0
            node.pressure = {}
            continue
        seized = node.spice_stock
        node.owner_id = conqueror_id
        _set_node_owner_links(state, node, old_owner, conqueror_id)
        node.pressure_accumulated = 0.0
        node.pressure = {}
        node.genome = state.factions[conqueror_id].genome[:]
        node.spice_stock = 0.0
        _sync_node_stock_to_resource(state, node)
        cap_id = state.factions[conqueror_id].capital_id
        state.nodes[cap_id].spice_stock += seized
        _sync_node_stock_to_resource(state, state.nodes[cap_id])
        _record_faction_action(
            state,
            conqueror_id,
            nid,
            "conquest",
            f"captured {nid} from {old_owner or 'neutral'}",
            resource_effects=[
                ResourceEffect(
                    resource_id=node.spice_resource_id,
                    effect_type="transfer",
                    quantity=float(seized),
                    source_id=node.node_actor_id,
                    target_id=state.nodes[cap_id].node_actor_id,
                )
            ],
            state_changes={
                "previous_owner": old_owner,
                "new_owner": conqueror_id,
                "node_id": nid,
            },
        )
        flipped.append(nid)
        old_label = old_owner if old_owner else "neutral"
        state.event_log.append(
            f"[tick {state.tick}] Node {nid} flipped {old_label} → {conqueror_id}"
            + (f" (seized {seized:.1f} spice)" if seized > 0 else "")
        )
    return flipped


# --------------------------------------------------------------------------- #
# Spice income — includes devastation-degraded base production                 #
# --------------------------------------------------------------------------- #


def _collect_income(state: SimState) -> None:
    """Add per-tick income to each owned node.

    income = spice_flow  (intrinsic, not degraded)
           + effective_base_production  (degraded by devastation)
    """
    cfg = state.config
    produced_totals: dict[str, float] = {}
    produced_nodes: dict[str, int] = {}
    for nid, node in state.nodes.items():
        if node.owner_id is not None:
            produced = _node_effective_production(node, cfg)
            node.spice_stock += produced
            _sync_node_stock_to_resource(state, node)
            produced_totals[node.owner_id] = produced_totals.get(node.owner_id, 0.0) + produced
            produced_nodes[node.owner_id] = produced_nodes.get(node.owner_id, 0) + 1

    for faction_id, total in produced_totals.items():
        capital_id = state.factions[faction_id].capital_id if faction_id in state.factions else faction_id
        _record_faction_action(
            state,
            faction_id,
            capital_id,
            "produce",
            f"produced {total:.2f} spice across {produced_nodes.get(faction_id, 0)} owned node(s)",
            state_changes={
                "total_produced": round(total, 6),
                "node_count": produced_nodes.get(faction_id, 0),
            },
        )


# --------------------------------------------------------------------------- #
# Stock cap — now accounts for devastation (multiplicative with logi cap)      #
# --------------------------------------------------------------------------- #


def _apply_stock_cap(state: SimState) -> None:
    """Clamp each owned node's stock to its effective cap (logi * devastation compound)."""
    for node in state.nodes.values():
        if node.owner_id is None or node.owner_id not in state.factions:
            continue
        cap = _node_effective_stock_cap(state, node)
        if node.spice_stock > cap:
            node.spice_stock = cap
            _sync_node_stock_to_resource(state, node)


# --------------------------------------------------------------------------- #
# Lab 11 genetics / secession (unchanged)                                      #
# --------------------------------------------------------------------------- #


def _visible_neighbor_faction_ids(
    state: SimState, faction: Faction, perception: Optional[Perception]
) -> set[str]:
    own_id = faction.faction_id
    if perception is not None:
        out: set[str] = set()
        for nid in perception.perceived_spaces.keys():
            if nid not in state.nodes:
                continue
            owner_id = state.nodes[nid].owner_id
            if owner_id is not None and owner_id != own_id:
                out.add(owner_id)
        return out
    return {
        fid
        for fid, f in state.factions.items()
        if fid != own_id and not f.is_eliminated
    }


def _compute_hamming_threshold(
    state: SimState, faction: Faction, perception: Optional[Perception]
) -> float:
    cfg = state.config
    cohe = faction.tech.cohe
    base = cfg.drift_threshold_bits + cohe * cfg.cohe_hamming_bonus
    neighbor_ids = _visible_neighbor_faction_ids(state, faction, perception)
    if not neighbor_ids:
        return max(float(cfg.min_hamming_threshold), base)
    neighbor_cohe_values = [
        state.factions[fid].tech.cohe for fid in neighbor_ids if fid in state.factions
    ]
    if not neighbor_cohe_values:
        return max(float(cfg.min_hamming_threshold), base)
    mean_neighbor_cohe = sum(neighbor_cohe_values) / len(neighbor_cohe_values)
    decay = max(0.0, mean_neighbor_cohe - cohe) * cfg.cohe_hamming_decay
    return max(float(cfg.min_hamming_threshold), base - decay)


def _mutate_and_check_secession(
    state: SimState,
    perceptions: "dict[str, Optional[Perception]] | None" = None,
) -> list[str]:
    if perceptions is None:
        perceptions = {}
    new_faction_ids: list[str] = []
    for faction in list(state.active_factions()):
        owned = state.nodes_owned_by(faction.faction_id)
        if not owned:
            continue
        bfs = _bfs_distances_state(state, faction.capital_id)
        perception = perceptions.get(faction.faction_id)
        effective_threshold = _compute_hamming_threshold(state, faction, perception)
        faction.effective_hamming_threshold = effective_threshold
        for nid in owned:
            node = state.nodes[nid]
            depth = bfs.get(nid, 1)
            if depth < 0:
                depth = len(state.nodes)
            p_mutate = min(1.0, state.config.mutation_rate * (depth + 1))
            if state._rng.random() < p_mutate:
                node.genome = _mutate_genome(node.genome, state._rng)
            _apply_centralization(state, faction, node)
            hamming = _hamming_distance(node.genome, faction.genome)
            if hamming >= effective_threshold:
                new_fid = _secede(state, nid, faction)
                new_faction_ids.append(new_fid)
    return new_faction_ids


def _secede(state: SimState, node_id: str, parent_faction: Faction) -> str:
    parent_faction.children_spawned += 1
    parent_suffix = parent_faction.faction_id.removeprefix("faction-")
    new_fid = f"faction-{parent_suffix}.{parent_faction.children_spawned}"
    while new_fid in state.factions:
        parent_faction.children_spawned += 1
        new_fid = f"faction-{parent_suffix}.{parent_faction.children_spawned}"
    node = state.nodes[node_id]
    new_genome = node.genome[:]
    new_faction = Faction(
        faction_id=new_fid,
        capital_id=node_id,
        genome=new_genome,
        behavior=_genome_to_ecloz(new_genome),
        color=_genome_to_color(new_genome),
    )
    new_faction.tech = TechVector(
        diplo=parent_faction.tech.diplo,
        cohe=parent_faction.tech.cohe,
        logi=parent_faction.tech.logi,
    )
    new_faction.tech_pending = TechVector(
        diplo=parent_faction.tech_pending.diplo,
        cohe=parent_faction.tech_pending.cohe,
        logi=parent_faction.tech_pending.logi,
    )
    state.factions[new_fid] = new_faction
    node.owner_id = new_fid
    new_faction.label = f"Faction {new_fid}"
    state.world.register_object(new_faction)
    state.world.place_object(new_faction.id, node_id, role="governs_from")
    _set_node_owner_links(state, node, parent_faction.faction_id, new_fid)
    node_actor = _registry_get_actor(state, node.node_actor_id)
    if node_actor is not None:
        node_actor.add_role("independent_political_unit")
    _record_faction_action(
        state,
        new_fid,
        node_id,
        "secession",
        f"node {node_id} seceded from {parent_faction.faction_id}",
        state_changes={
            "node_id": node_id,
            "from": parent_faction.faction_id,
            "to": new_fid,
        },
    )
    state.event_log.append(
        f"[tick {state.tick}] SECESSION: node {node_id} broke from "
        f"{parent_faction.faction_id} → new faction {new_fid}"
    )
    return new_fid


# --------------------------------------------------------------------------- #
# Victory check (unchanged)                                                    #
# --------------------------------------------------------------------------- #


def _check_victory(state: SimState) -> None:
    total = len(state.nodes)
    for faction in state.active_factions():
        owned = len(state.nodes_owned_by(faction.faction_id))
        if owned == total:
            state.game_over = True
            state.winner_id = faction.faction_id
            state.event_log.append(
                f"[tick {state.tick}] {faction.faction_id} controls all nodes — VICTORY"
            )
            return
    if state.config.max_ticks > 0 and state.tick >= state.config.max_ticks:
        best = max(
            state.active_factions(),
            key=lambda f: len(state.nodes_owned_by(f.faction_id)),
        )
        state.game_over = True
        state.winner_id = best.faction_id
        state.event_log.append(
            f"[tick {state.tick}] Max ticks reached. Winner: {best.faction_id}"
        )


def _connected_components(state: SimState) -> list[list[str]]:
    adj: dict[str, list[str]] = {nid: [] for nid in state.nodes}
    for a, b in state.links:
        adj[a].append(b)
        adj[b].append(a)
    seen: set[str] = set()
    components: list[list[str]] = []
    for nid in state.nodes:
        if nid in seen:
            continue
        comp: list[str] = []
        queue = [nid]
        seen.add(nid)
        head = 0
        while head < len(queue):
            cur = queue[head]
            head += 1
            comp.append(cur)
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb)
                    queue.append(nb)
        components.append(comp)
    return components


def _add_runtime_link(state: SimState, a: str, b: str, capacity: float) -> bool:
    if a == b:
        return False
    key = (min(a, b), max(a, b))
    if key in state.links:
        return False
    state.links[key] = Link(source_id=key[0], target_id=key[1], max_flow=capacity)
    rel = SpaceRelation(
        source_space_id=key[0], target_space_id=key[1], relation_type="adjacent_to"
    )
    state.relation_graph.add_relation(rel)
    state.world.space_relation_graph.add_relation(rel)
    return True


def _apply_globalization(state: SimState) -> None:
    growth_p = state.config.globalization_link_growth_chance
    bridge_p = state.config.globalization_bridge_spawn_chance
    roll = state._rng.random()
    if roll < growth_p and state.links:
        key = state._rng.choice(list(state.links.keys()))
        lnk = state.links[key]
        lnk.max_flow += 1.0
        state.event_log.append(
            f"[tick {state.tick}] GLOBALIZATION: link {key[0]}-{key[1]} "
            f"capacity +1 → {lnk.max_flow:.1f}"
        )
        return
    if roll >= growth_p + bridge_p:
        return
    components = _connected_components(state)
    if len(components) < 2:
        return
    c1, c2 = state._rng.sample(components, 2)
    a = state._rng.choice(c1)
    b = state._rng.choice(c2)
    if _add_runtime_link(state, a, b, capacity=1.0):
        state.event_log.append(
            f"[tick {state.tick}] GLOBALIZATION: new bridge {min(a,b)}-{max(a,b)} created"
        )


# --------------------------------------------------------------------------- #
# Technology pipeline (unchanged from Lab 11)                                  #
# --------------------------------------------------------------------------- #

_SQRT2_INV: float = 1.0 / math.sqrt(2.0)
_DIPLO_LOGI_AXIS: tuple[float, float, float] = (_SQRT2_INV, 0.0, _SQRT2_INV)
_COHE_LOGI_AXIS: tuple[float, float, float] = (0.0, _SQRT2_INV, _SQRT2_INV)


def _extract_tech_signals(
    state: SimState, faction: Faction, perception: Optional[Perception] = None
) -> dict:
    faction_id = faction.faction_id
    owned = state.nodes_owned_by(faction_id)
    if perception is not None:
        known_nodes = list(perception.perceived_spaces.keys())
    else:
        known_nodes = list(state.nodes.keys())
    total_nodes = max(1, len(state.nodes))
    known_count = max(1, len(known_nodes))
    owned_count = len(owned)
    owned_fraction = owned_count / known_count
    known_ratio = known_count / total_nodes
    relations: dict[str, float] = {}
    for nid in known_nodes:
        other_owner = state.nodes[nid].owner_id
        if other_owner is not None and other_owner != faction_id:
            rel = state.relation_between(faction_id, other_owner)
            if rel is not None:
                relations[other_owner] = rel
    mean_relation = sum(relations.values()) / len(relations) if relations else 0.5
    min_relation = min(relations.values()) if relations else 0.5
    total_pressure = sum(state.nodes[nid].pressure_accumulated for nid in owned)
    mean_pressure = total_pressure / max(1, owned_count)
    disconnected_owned = 0
    if perception is not None:
        perceived_adj: dict[str, list[str]] = {nid: [] for nid in known_nodes}
        for perceived_rel in perception.perceived_relations:
            inner = perceived_rel.relation
            if inner.relation_type == "adjacent_to":
                a, b = inner.source_space_id, inner.target_space_id
                if a in perceived_adj:
                    perceived_adj[a].append(b)
                if b in perceived_adj:
                    perceived_adj[b].append(a)
        seen: set[str] = {faction.capital_id}
        bfs_q: list[str] = [faction.capital_id]
        bfs_head = 0
        while bfs_head < len(bfs_q):
            cur = bfs_q[bfs_head]
            bfs_head += 1
            for nb in perceived_adj.get(cur, []):
                if nb not in seen:
                    seen.add(nb)
                    bfs_q.append(nb)
        for nid in owned:
            if nid not in seen:
                disconnected_owned += 1
    else:
        bfs = _bfs_distances_state(state, faction.capital_id)
        for nid in owned:
            if bfs.get(nid, -1) < 0:
                disconnected_owned += 1
    return {
        "known_nodes": known_nodes,
        "owned_fraction": owned_fraction,
        "relations": relations,
        "mean_relation": mean_relation,
        "min_relation": min_relation,
        "disconnected_owned": disconnected_owned,
        "total_pressure_received": total_pressure,
        "mean_pressure_received": mean_pressure,
        "known_ratio": known_ratio,
    }


def _compute_tech_alpha(signals: dict, config: SimConfig) -> tuple[float, float, float]:
    pressure_norm = _clamp01(
        signals["total_pressure_received"] / max(1.0, config.flip_threshold)
    )
    mean_rel_inv = 1.0 - signals["mean_relation"]
    min_rel_inv = 1.0 - signals["min_relation"]
    owned_frac = signals["owned_fraction"]
    owned_frac_inv = 1.0 - owned_frac
    disconnected_norm = _clamp01(
        signals["disconnected_owned"] / max(1, len(signals["known_nodes"]))
    )
    known_ratio_inv = 1.0 - signals["known_ratio"]
    alpha_diplo = (
        config.tech_alpha_weight_pressure_diplo * pressure_norm
        + config.tech_alpha_weight_relation_inv_diplo * mean_rel_inv
        + config.tech_alpha_weight_min_relation_inv_diplo * min_rel_inv
        + config.tech_alpha_weight_owned_fraction_inv_diplo * owned_frac_inv
        + config.tech_alpha_weight_known_ratio_inv_diplo * known_ratio_inv
    )
    alpha_cohe = (
        config.tech_alpha_weight_disconnected_cohe * disconnected_norm
        + config.tech_alpha_weight_owned_fraction_cohe * owned_frac
    )
    alpha_logi = (
        config.tech_alpha_weight_pressure_logi * pressure_norm
        + config.tech_alpha_weight_owned_fraction_logi * owned_frac
        + config.tech_alpha_weight_known_ratio_inv_logi * known_ratio_inv
    )
    return _normalize_3d(alpha_diplo, alpha_cohe, alpha_logi)


def _compute_tech_investment_debug(
    state: SimState, faction: Faction, perception: Optional[Perception] = None
) -> tuple[TechVector, TechVector]:
    cfg = state.config
    behavior = faction.behavior
    v0 = _random_unit_sphere_3d(state._rng)
    signals = _extract_tech_signals(state, faction, perception)
    pressure_sig = _clamp01(
        signals["total_pressure_received"] / max(1.0, cfg.flip_threshold)
    )
    rel_sig = 1.0 - signals["mean_relation"]
    frac_sig = 1.0 - signals["owned_fraction"]
    signal_strength = max(pressure_sig, rel_sig, frac_sig)
    trigger_val = _clamp01(signal_strength + 1.0 - behavior.engagement_threshold)
    v1 = (v0[0] * trigger_val, v0[1] * trigger_val, v0[2] * trigger_val)
    C = behavior.concentration
    history = faction.tech_investment_history
    last_mag = (
        _magnitude_3d(history[-1].diplo, history[-1].cohe, history[-1].logi)
        if history
        else 0.0
    )
    burst_threshold = 0.3 + C * 0.4
    intensity = max(0.0, 1.0 - C) if last_mag > burst_threshold else (1.0 + C)
    v2 = (v1[0] * intensity, v1[1] * intensity, v1[2] * intensity)
    alpha = _compute_tech_alpha(signals, cfg)
    O = behavior.objective_bias
    bias = (
        O * _DIPLO_LOGI_AXIS[0] + (1.0 - O) * _COHE_LOGI_AXIS[0],
        O * _DIPLO_LOGI_AXIS[1] + (1.0 - O) * _COHE_LOGI_AXIS[1],
        O * _DIPLO_LOGI_AXIS[2] + (1.0 - O) * _COHE_LOGI_AXIS[2],
    )
    v2_mag = _magnitude_3d(*v2)
    if v2_mag > 1e-12:
        deformation = (alpha[0] * bias[0], alpha[1] * bias[1], alpha[2] * bias[2])
        v3_raw = (
            v2[0] + deformation[0],
            v2[1] + deformation[1],
            v2[2] + deformation[2],
        )
        v3_raw_mag = _magnitude_3d(*v3_raw)
        if v3_raw_mag > 1e-12:
            v3 = (
                v3_raw[0] / v3_raw_mag * v2_mag,
                v3_raw[1] / v3_raw_mag * v2_mag,
                v3_raw[2] / v3_raw_mag * v2_mag,
            )
        else:
            v3 = v2
    else:
        v3 = v2
    L = behavior.liquidity_preference
    total_spice = state.total_spice_for(faction.faction_id)
    spend_rate = _clamp01(
        1.0 - L * _clamp01(total_spice / max(cfg.tech_reserve_reference, 1e-9))
    )
    v4 = (v3[0] * spend_rate, v3[1] * spend_rate, v3[2] * spend_rate)
    Z = behavior.centralization
    if history:
        window_vecs = history[-cfg.tech_rnd_history_window :]
        n = len(window_vecs)
        hist_mean = (
            sum(h.diplo for h in window_vecs) / n,
            sum(h.cohe for h in window_vecs) / n,
            sum(h.logi for h in window_vecs) / n,
        )
        v5 = (
            Z * hist_mean[0] + (1.0 - Z) * v4[0],
            Z * hist_mean[1] + (1.0 - Z) * v4[1],
            Z * hist_mean[2] + (1.0 - Z) * v4[2],
        )
    else:
        v5 = v4
    base_cost = cfg.transport_base_cost
    planned_spend = sum(
        amt + base_cost for _, _, amt in faction.move_orders + faction.admin_orders
    )
    available = max(0.0, total_spice - planned_spend)
    v5_mag = _magnitude_3d(*v5)
    required = v5_mag * cfg.tech_rnd_base_cost
    eco_scale = min(1.0, max(0.5, available / required)) if required > 1e-12 else 1.0
    v6 = (v5[0] * eco_scale, v5[1] * eco_scale, v5[2] * eco_scale)
    faction.tech_alpha = alpha
    inv_scale = cfg.tech_investment_scale
    return (
        TechVector(
            diplo=v6[0] * inv_scale, cohe=v6[1] * inv_scale, logi=v6[2] * inv_scale
        ),
        TechVector(
            diplo=v5[0] * inv_scale, cohe=v5[1] * inv_scale, logi=v5[2] * inv_scale
        ),
    )


def _compute_tech_investment(
    state: SimState, faction: Faction, perception: Optional[Perception] = None
) -> TechVector:
    v6, _ = _compute_tech_investment_debug(state, faction, perception)
    return v6


def _compute_rubberband_multipliers(state: SimState, faction: Faction) -> TechVector:
    cfg = state.config
    all_active = state.active_factions()
    fid = faction.faction_id
    border_neighbor_fids: set[str] = set()
    for nid in state.nodes_owned_by(fid):
        for nb in state.neighbors_of(nid):
            other_owner = state.nodes[nb].owner_id
            if other_owner is not None and other_owner != fid:
                border_neighbor_fids.add(other_owner)
    result = TechVector(diplo=1.0, cohe=1.0, logi=1.0)
    for axis in ("diplo", "cohe", "logi"):
        faction_level: float = getattr(faction.tech, axis)
        max_level = max((getattr(f.tech, axis) for f in all_active), default=0.0)
        leader_mult = (
            1.0 + cfg.tech_leader_cost_multiplier
            if max_level > 1e-9 and faction_level >= max_level - 1e-9
            else 1.0
        )
        neighbor_mult = 1.0
        for nbfid in border_neighbor_fids:
            if nbfid not in state.factions:
                continue
            gap = getattr(state.factions[nbfid].tech, axis) - faction_level
            if gap > 0.0:
                neighbor_mult *= max(0.1, 1.0 - cfg.tech_neighbor_acceleration * gap)
        setattr(result, axis, leader_mult * neighbor_mult)
    return result


def _apply_tech_effects(state: SimState) -> None:
    window = state.config.tech_rnd_history_window
    for faction in state.factions.values():
        if faction.is_eliminated:
            continue
        pending = faction.tech_pending
        if pending.diplo > 0.0 or pending.cohe > 0.0 or pending.logi > 0.0:
            faction.tech_investment_history.append(pending)
            if len(faction.tech_investment_history) > window:
                faction.tech_investment_history = faction.tech_investment_history[
                    -window:
                ]
        rb = _compute_rubberband_multipliers(state, faction)

        def _gain(current: float, raw_gain: float, rb_mult: float) -> float:
            return _clamp01(current + raw_gain / max(rb_mult, 1e-9))

        faction.tech = TechVector(
            diplo=_gain(faction.tech.diplo, pending.diplo, rb.diplo),
            cohe=_gain(faction.tech.cohe, pending.cohe, rb.cohe),
            logi=_gain(faction.tech.logi, pending.logi, rb.logi),
        )
        faction.tech_pending = TechVector()


# --------------------------------------------------------------------------- #
# Main tick step                                                               #
# --------------------------------------------------------------------------- #


def step(state: SimState) -> None:
    """Advance the simulation by one tick.

    Order:
    1.  Reset link usage
    2.  Apply tech effects from previous tick
    3.  Collect income (spice_flow + effective base production)
    4.  Globalization event
    5.  Per-faction: symbolic deliberation, plan moves, plan centralization, tech pipeline
    6.  Execute transport
    7.  Apply conquest → returns flipped list
    8.  Update devastation (increment flipped, decrement stable)
    9.  Apply stock cap (now uses devastation-adjusted effective cap)
    10. Grow relations
    11. Mutate genomes / check secession
    12. Check victory
    13. Increment tick
    """
    if state.game_over:
        return

    state.latest_action_ids = []
    _reset_link_usage(state)
    _apply_tech_effects(state)
    _collect_income(state)
    _apply_globalization(state)

    perceptions: dict[str, Optional[Perception]] = {}
    for faction in state.active_factions():
        perception = None
        if state.config.perception_mode == "limited":
            perception = get_faction_perception(state, faction.faction_id)
        perceptions[faction.faction_id] = perception
        _run_symbolic_deliberation(state, faction, perception)
        _plan_moves(state, faction, perception)
        _plan_centralization(state, faction)
        faction.tech_pending = _compute_tech_investment(state, faction, perception)

    _execute_transport(state)
    flipped = _apply_conquest(state)  # Lab 12: capture flip list
    _update_devastation(state, flipped)  # Lab 12: update devastation scores
    _apply_stock_cap(state)  # uses devastation-adjusted cap
    _grow_relations(state)
    _mutate_and_check_secession(state, perceptions)
    _check_victory(state)

    state.tick += 1


# --------------------------------------------------------------------------- #
# Initialisation                                                               #
# --------------------------------------------------------------------------- #


def create_sim(config: SimConfig) -> SimState:
    config.validate()
    rng = random.Random(config.seed)
    raw = build_graph(config)

    world = World(id="lab13-ometeotl-retrofit-world")
    relation_graph = SpaceRelationGraph()

    for raw_node in raw.nodes:
        space = Space(id=raw_node.node_id)
        space.label = raw_node.node_id
        world.add_space(space)

    links: dict[tuple[str, str], Link] = {}
    for a, b in raw.edges:
        rel = SpaceRelation(
            source_space_id=a, target_space_id=b, relation_type="adjacent_to"
        )
        relation_graph.add_relation(rel)
        world.space_relation_graph.add_relation(rel)
        cap = rng.uniform(config.min_link_flow, config.max_link_flow)
        key = (min(a, b), max(a, b))
        links[key] = Link(source_id=min(a, b), target_id=max(a, b), max_flow=cap)

    node_ids = raw.all_node_ids()
    rng.shuffle(node_ids)
    capital_ids = node_ids[: config.num_factions]

    factions: dict[str, Faction] = {}
    for i, cap_id in enumerate(capital_ids):
        fid = f"faction-{i}"
        genome = _random_genome(config.genome_length, rng)
        faction = Faction(
            faction_id=fid,
            capital_id=cap_id,
            genome=genome,
            behavior=_genome_to_ecloz(genome),
            color=_genome_to_color(genome),
        )
        factions[fid] = faction
        faction.label = f"Faction {i}"
        world.register_object(faction)
        world.place_object(faction.id, cap_id, role="governs_from")

    capital_to_faction: dict[str, str] = {
        f.capital_id: fid for fid, f in factions.items()
    }
    nodes: dict[str, Node] = {}
    for raw_node in raw.nodes:
        nid = raw_node.node_id
        if nid in capital_to_faction:
            fid = capital_to_faction[nid]
            owner = fid
            genome = factions[fid].genome[:]
        else:
            owner = None
            genome = [0] * config.genome_length

        spice_resource_id = f"resource-spice-{nid}"
        spice_resource = Resource(id=spice_resource_id)
        spice_resource.label = f"Spice Stock {nid}"
        spice_resource.kind = "spice"
        spice_resource.resource_mode = "stock"
        spice_resource.rivalry = "rival"
        spice_resource.transferability = "transferable"
        spice_resource.divisibility = "divisible"
        spice_resource.state["quantity"] = float(config.initial_node_spice)
        world.register_object(spice_resource)
        world.place_object(spice_resource.id, nid, role="stored_in")

        node_obj = Node(
            node_id=nid,
            spice_flow=raw_node.spice_flow,
            x=raw_node.x,
            y=raw_node.y,
            owner_id=owner,
            genome=genome,
            spice_stock=config.initial_node_spice,
            spice_resource_id=spice_resource_id,
        )
        node_obj.label = f"Node Actor {nid}"
        node_obj.add_relation("resource", spice_resource.id)
        world.register_object(node_obj)
        world.place_object(node_obj.id, nid, role="located_in")
        nodes[nid] = node_obj

    state = SimState(
        config=config,
        world=world,
        relation_graph=relation_graph,
        nodes=nodes,
        factions=factions,
        links=links,
    )
    state._rng = random.Random(rng.randint(0, 2**32 - 1))
    for node in state.nodes.values():
        _set_node_owner_links(
            state, node, old_owner_id=None, new_owner_id=node.owner_id
        )
        _sync_node_stock_to_resource(state, node)
    state.event_log.append(
        f"[tick 0] Simulation started (Lab 13 - Ometeotl Retro-Fit). "
        f"{config.num_factions} factions, {config.num_nodes} nodes, "
        f"perception_mode={config.perception_mode}."
    )
    return state


# --------------------------------------------------------------------------- #
# Serialisation                                                                #
# --------------------------------------------------------------------------- #


def serialize_state(state: SimState) -> dict:
    factions_out = {}
    for fid, faction in state.factions.items():
        owned = state.nodes_owned_by(fid)
        factions_out[fid] = {
            "faction_id": fid,
            "actor_id": faction.actor_id or fid,
            "capital_id": faction.capital_id,
            "color": faction.color,
            "genome": faction.genome,
            "genome_str": "".join(str(b) for b in faction.genome),
            "behavior": {
                "engagement_threshold": round(faction.behavior.engagement_threshold, 3),
                "concentration": round(faction.behavior.concentration, 3),
                "liquidity_preference": round(faction.behavior.liquidity_preference, 3),
                "objective_bias": round(faction.behavior.objective_bias, 3),
                "centralization": round(faction.behavior.centralization, 3),
            },
            "total_spice": round(state.total_spice_for(fid), 2),
            "spice_income": state.spice_income_for(fid),
            "node_count": len(owned),
            "is_eliminated": faction.is_eliminated,
            "move_orders": [
                {"from": s, "to": d, "amount": round(a, 2)}
                for s, d, a in faction.move_orders
            ],
            "admin_orders": [
                {"from": s, "to": d, "amount": round(a, 2)}
                for s, d, a in faction.admin_orders
            ],
            "symbolic": (
                {
                    "mode": faction.symbolic_intent.mode,
                    "goal_id": faction.symbolic_intent.goal.id,
                    "goal_priority": round(faction.symbolic_intent.goal.priority, 3),
                    "strategy_id": faction.symbolic_intent.strategy.id,
                }
                if faction.symbolic_intent is not None
                else None
            ),
            "tech": {
                "diplo": round(faction.tech.diplo, 4),
                "cohe": round(faction.tech.cohe, 4),
                "logi": round(faction.tech.logi, 4),
            },
            "tech_investment": {
                "diplo": round(faction.tech_pending.diplo, 4),
                "cohe": round(faction.tech_pending.cohe, 4),
                "logi": round(faction.tech_pending.logi, 4),
            },
            "tech_alpha": {
                "diplo": round(faction.tech_alpha[0], 4),
                "cohe": round(faction.tech_alpha[1], 4),
                "logi": round(faction.tech_alpha[2], 4),
            },
            "effective_hamming_threshold": round(
                faction.effective_hamming_threshold, 3
            ),
            "recent_action_ids": faction.recent_action_ids[-8:],
            "perceived_relations": {
                other_fid: round(rel, 3)
                for other_fid in state.factions
                if other_fid != fid
                for rel in [_get_perceived_relation(state, fid, other_fid)]
                if rel is not None
            },
        }

    nodes_out = []
    for nid, node in state.nodes.items():
        eff_cap = (
            _node_effective_stock_cap(state, node)
            if node.owner_id and node.owner_id in state.factions
            else float(state.config.base_stock_cap)
        )
        eff_prod = _node_effective_production(node, state.config)
        flip_count = sum(
            1
            for t in node.flip_tick_history
            if state.tick - t < state.config.devastation_window_size
        )
        nodes_out.append(
            {
                "node_id": nid,
                "node_actor_id": node.node_actor_id,
                "spice_resource_id": node.spice_resource_id,
                "spice_flow": node.spice_flow,
                "spice_stock": round(node.spice_stock, 2),
                "x": node.x,
                "y": node.y,
                "owner_id": node.owner_id,
                "color": (
                    state.factions[node.owner_id].color
                    if node.owner_id and node.owner_id in state.factions
                    else "#cccccc"
                ),
                "genome_str": "".join(str(b) for b in node.genome),
                "pressure_accumulated": round(node.pressure_accumulated, 2),
                "stock_cap": round(eff_cap, 2),
                # Lab 12 audit fields
                "devastation": round(node.devastation, 4),
                "effective_stock_cap": round(eff_cap, 2),
                "effective_production": round(eff_prod, 4),
                "flip_count_in_window": flip_count,
            }
        )

    edges_out = []
    for r in state.relation_graph.relations:
        if r.relation_type == "adjacent_to":
            key = (
                min(r.source_space_id, r.target_space_id),
                max(r.source_space_id, r.target_space_id),
            )
            lnk = state.links.get(key)
            edges_out.append(
                {
                    "a": r.source_space_id,
                    "b": r.target_space_id,
                    "max_flow": round(lnk.max_flow, 1) if lnk else None,
                    "used_flow": round(lnk.used_flow, 1) if lnk else None,
                }
            )

    relations_out = [
        {"a": a, "b": b, "value": round(value, 3)}
        for (a, b), value in sorted(state.relations.items())
    ]

    return {
        "tick": state.tick,
        "game_over": state.game_over,
        "winner_id": state.winner_id,
        "factions": factions_out,
        "nodes": nodes_out,
        "edges": edges_out,
        "relations": relations_out,
        "latest_action_ids": state.latest_action_ids[-30:],
        "event_log": state.event_log[-20:],
        "config": state.config.to_dict(),
    }
