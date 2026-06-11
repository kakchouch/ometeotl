"""Core simulation engine for Lab 10 — Complex Behavior Simulation.

Key differences from Lab 3:
- Spice stock is stored in Node, NOT in Faction (logistics layer)
- Graph links have a max_flow capacity (transport bottleneck)
- Every shipment burns a flat base cost (transport_base_cost) regardless of size
  → many scattered small moves are expensive; one large focused move is cheap
- Additionally a proportional fee (transport_gas_fee) is destroyed per hop
- Conquest pressure comes from spice explicitly routed to enemy/neutral nodes
- Unallocated spice on a flipped node is seized by the conqueror

Ometeotl is used for the ontological / relational graph layer:
  World + Space (nodes) + SpaceRelation (adjacency) + SpaceRelationGraph
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from ometeotl_core.model.goals import Goal
from ometeotl_core.model.strategies import Strategy, StrategyNode
from ometeotl_core.model.spaces import Space
from ometeotl_core.model.space_relations import SpaceRelation, SpaceRelationGraph
from ometeotl_core.model.world import World
from ometeotl_core.model.perception import Perception

from .config import SimConfig
from .graph_gen import RawGraph, build_graph, bfs_distances
from .perception import get_faction_perception, visible_border_targets

# --------------------------------------------------------------------------- #
# Genome utilities                                                              #
# --------------------------------------------------------------------------- #


def _random_genome(length: int, rng: random.Random) -> list[int]:
    """Return a genome as a list of bits (each 0 or 1)."""
    return [rng.randint(0, 1) for _ in range(length)]


def _hamming_distance(a: list[int], b: list[int]) -> int:
    """Count bit positions where *a* and *b* differ."""
    return sum(x != y for x, y in zip(a, b))


def _mutate_genome(genome: list[int], rng: random.Random) -> list[int]:
    """Flip one random bit and return the new genome (original is not mutated)."""
    idx = rng.randrange(len(genome))
    new = genome[:]
    new[idx] = 1 - new[idx]
    return new


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _genome_to_ecloz(genome: list[int]) -> BehaviorProfile:
    """Derive the ECLOZ behavior profile deterministically from the genome bitfield.

    Bits are assigned to the 5 axes by position mod 5, so axis k owns bits
    k, k+5, k+10, …  Each axis value = mean of its bits ∈ [0, 1].

    A single-bit mutation shifts at most one axis by 1/⌈N/5⌉, keeping ECLOZ
    stable under small perturbations while remaining sensitive to accumulated
    genetic change.  Works for any N ≥ 1.
    """
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


def _apply_centralization(state: SimState, faction: Faction, node: Node) -> int:
    """Spend node-resident spice to reduce drift on a node.

    Z = 1 corrects all affordable drift; Z = 0 does nothing.
    """
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
    state.admin_delivery_budget[node.node_id] = max(0.0, available_budget - spent)
    state.event_log.append(
        f"[tick {state.tick}] ADMIN: {faction.faction_id} spent {spent:.1f} spice "
        f"to suppress drift on {node.node_id} by {corrections} bit(s)"
    )
    return corrections


# --------------------------------------------------------------------------- #
# Data types                                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class Node:
    """Runtime state for one graph node.

    Spice stock lives HERE, not in the faction.
    """

    node_id: str
    spice_flow: int
    x: float  # UI position, normalised [0..1]
    y: float
    owner_id: str | None  # faction id or None (neutral)
    genome: list[int]  # node's local genome copy (all zeros for neutral)
    # Spice physically located at this node
    spice_stock: float = 0.0
    # Conquest pressure applied this tick by each attacker: {faction_id: amount}
    pressure: dict[str, float] = field(default_factory=dict)
    # Total cumulative pressure (resets on flip or successful defence)
    pressure_accumulated: float = 0.0


@dataclass
class Link:
    """Transport link between two nodes (undirected, stored with min/max key)."""

    source_id: str
    target_id: str
    max_flow: float  # maximum spice that can transit per tick
    used_flow: float = 0.0  # committed this tick (reset each tick)


@dataclass
class BehaviorProfile:
    """Behavior matrix for one faction.

    Axes (all in [0, 1]):
    - engagement_threshold: willingness to engage offense.
    - concentration: focus on fewer targets (high) vs spread (low).
    - liquidity_preference: keep reserves (high) vs spend now (low).
    - objective_bias: offense/territory (high) vs defense/economy (low).
    - centralization: willingness to spend spice on drift suppression.
    """

    engagement_threshold: float
    concentration: float
    liquidity_preference: float
    objective_bias: float
    centralization: float


@dataclass
class SymbolicIntent:
    """Symbolic teleology bundle driving one faction for one tick."""

    goal: Goal
    strategy: Strategy
    mode: str
    engagement_shift: float = 0.0
    concentration_shift: float = 0.0
    liquidity_shift: float = 0.0
    objective_shift: float = 0.0
    centralization_shift: float = 0.0


@dataclass
class Faction:
    """Runtime state for one faction.

    Note: spice_stock has been removed.  Spice now lives in Node.spice_stock.
    """

    faction_id: str
    capital_id: str
    genome: list[int]
    behavior: BehaviorProfile
    color: str = "#888888"
    # Move orders planned this tick: list of (from_node, to_node, amount)
    move_orders: list[tuple[str, str, float]] = field(default_factory=list)
    # Administrative orders planned this tick: list of (from_node, to_node, amount)
    admin_orders: list[tuple[str, str, float]] = field(default_factory=list)
    symbolic_intent: SymbolicIntent | None = None
    is_eliminated: bool = False


@dataclass
class SimState:
    """Full mutable runtime state of the simulation."""

    config: SimConfig
    world: World
    relation_graph: SpaceRelationGraph
    nodes: dict[str, Node]  # node_id → Node
    factions: dict[str, Faction]  # faction_id → Faction
    links: dict[tuple[str, str], Link]  # (min_id, max_id) → Link
    tick: int = 0
    game_over: bool = False
    winner_id: str | None = None
    event_log: list[str] = field(default_factory=list)
    relations: dict[tuple[str, str], float] = field(default_factory=dict)
    admin_delivery_budget: dict[str, float] = field(default_factory=dict)
    _rng: random.Random = field(default_factory=random.Random, repr=False)

    # ------------------------------------------------------------------ #
    # Derived queries                                                       #
    # ------------------------------------------------------------------ #

    def neighbors_of(self, node_id: str) -> list[str]:
        return self.relation_graph.neighbors_of(node_id)

    def nodes_owned_by(self, faction_id: str) -> list[str]:
        return [nid for nid, n in self.nodes.items() if n.owner_id == faction_id]

    def border_targets_for(self, faction_id: str) -> list[str]:
        """Return nodes adjacent to *faction_id*'s territory that are not owned by it."""
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
        """Total spice physically held in nodes owned by this faction."""
        return sum(
            self.nodes[nid].spice_stock for nid in self.nodes_owned_by(faction_id)
        )

    def link_remaining(self, a: str, b: str) -> float:
        """Remaining transport capacity on the link between a and b this tick."""
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


# --------------------------------------------------------------------------- #
# Colour derived from genome                                                   #
# --------------------------------------------------------------------------- #

def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convert HSL (h in degrees 0–360, s/l in [0,1]) to #rrggbb hex."""
    c = (1.0 - abs(2.0 * l - 1.0)) * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = l - c / 2.0
    sector = int(h / 60.0) % 6
    r1, g1, b1 = [
        (c, x, 0.0), (x, c, 0.0), (0.0, c, x),
        (0.0, x, c), (x, 0.0, c), (c, 0.0, x),
    ][sector]
    r = max(0, min(255, round((r1 + m) * 255)))
    g = max(0, min(255, round((g1 + m) * 255)))
    b = max(0, min(255, round((b1 + m) * 255)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _genome_to_color(genome: list[int]) -> str:
    """Derive a faction color from the genome via circular projection.

    Each bit i projects a unit vector at angle 2π·i/L onto the unit circle.
    Hue = direction of the resultant vector (all bits contribute equally; no
    fixed bit-to-channel mapping; invariant to genome length).
    A single bit flip shifts the resultant by at most arcsin(1/M) where M is
    the current magnitude — typically ≤ 20–30° for random genomes.
    Lightness = overall bit mean (0.35–0.55); saturation fixed at 0.75.
    """
    L = len(genome)
    if L == 0:
        return "#888888"
    cx = sum(genome[i] * math.cos(2.0 * math.pi * i / L) for i in range(L))
    cy = sum(genome[i] * math.sin(2.0 * math.pi * i / L) for i in range(L))
    mag = math.hypot(cx, cy)
    hue = (math.degrees(math.atan2(cy, cx))) % 360.0 if mag > 1e-9 else 0.0
    lum = 0.35 + (sum(genome) / L) * 0.20  # 0.35–0.55
    return _hsl_to_hex(hue, 0.75, lum)


# --------------------------------------------------------------------------- #
# BFS distance within SimState                                                 #
# --------------------------------------------------------------------------- #


def _bfs_distances_state(state: SimState, source: str) -> dict[str, int]:
    """BFS over the relation graph from *source*."""
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
    state: SimState,
    source: str,
    visible_ids: set[str],
) -> dict[str, int]:
    """BFS from *source* restricted to *visible_ids*."""
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



def _relation_pressure_factor(
    state: SimState, attacker_id: str, defender_id: str
) -> float:
    """Return offense multiplier from relation level.

    High relation -> lower aggression. Low relation -> higher aggression.
    """
    rel = state.relation_between(attacker_id, defender_id)
    if rel is None:
        return 1.0
    bias = state.config.relation_offense_bias
    # rel=1 -> 1-bias, rel=0 -> 1+bias
    return max(0.05, 1.0 + bias * (1.0 - 2.0 * rel))


def _effective_behavior(faction: Faction) -> BehaviorProfile:
    """Return base behavior adjusted by the faction symbolic intent."""
    base = faction.behavior
    intent = faction.symbolic_intent
    if intent is None:
        return base
    return BehaviorProfile(
        engagement_threshold=_clamp01(base.engagement_threshold + intent.engagement_shift),
        concentration=_clamp01(base.concentration + intent.concentration_shift),
        liquidity_preference=_clamp01(base.liquidity_preference + intent.liquidity_shift),
        objective_bias=_clamp01(base.objective_bias + intent.objective_shift),
        centralization=_clamp01(base.centralization + intent.centralization_shift),
    )


def _symbolic_snapshot(
    state: SimState,
    faction: Faction,
    perception: Optional[Perception] = None,
) -> dict[str, float]:
    """Compute high-level signals used by symbolic deliberation."""
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
        visible_faction_ids = {
            state.nodes[nid].owner_id
            for nid in visible_ids
            if state.nodes[nid].owner_id not in (None, faction.faction_id)
        }
    else:
        visible_faction_ids = set(state.factions.keys()) - {faction.faction_id}
    for other_fid in visible_faction_ids:
        rel = state.relation_between(faction.faction_id, other_fid)
        if rel is not None:
            relation_values.append(rel)
    mean_relation = sum(relation_values) / len(relation_values) if relation_values else 0.5

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
    state: SimState,
    faction: Faction,
    snapshot: dict[str, float],
) -> SymbolicIntent:
    """Build teleological objects (Goal + Strategy) and map them to behavior shifts.
    
    Faction personality (E/C/L/O/Z) skews mode selection and shift magnitude:
    - engagement: defensive (high) → stabilize/reconcile, offensive (low) → expand
    - concentration: high → expand (focus), low → connect
    - liquidity: conservative (high) → reconcile/balanced, aggressive (low) → expand
    - objective: defensive (low) → stabilize, offensive (high) → expand
    - centralization: high → stabilize, low → expand/connect
    """
    fid = faction.faction_id
    tick = state.tick
    pressure = snapshot["mean_pressure"]
    node_share = snapshot["node_share"]
    mean_relation = snapshot["mean_relation"]
    disconnected_ratio = snapshot["disconnected_ratio"]
    
    behavior = faction.behavior

    # Base mode from context signals
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
    
    # Personality-based mode adjustment (boost priority for aligned modes)
    if behavior.engagement_threshold > 0.65 and mode in ("expand", "connect"):
        # High engagement threshold → conservative, prefer stabilize
        mode = "stabilize"
        priority = 0.8
    elif behavior.engagement_threshold < 0.35 and mode == "reconcile":
        # Low engagement threshold → aggressive, prefer expand
        mode = "expand"
        priority = 0.85
    elif behavior.concentration > 0.7 and mode != "expand":
        # High concentration → focused on few targets, favor expand
        priority = max(priority, 0.80)
    elif behavior.liquidity_preference > 0.65 and mode == "expand":
        # High liquidity (conservative) → avoid aggressive expand
        mode = "reconcile"
        priority = 0.75
    elif behavior.objective_bias > 0.7 and mode in ("stabilize", "reconcile"):
        # Offensive bias → drift toward expand if not under pressure
        if pressure < state.config.flip_threshold * 0.10:
            mode = "expand"
            priority = 0.80
    elif behavior.centralization < 0.3 and mode == "stabilize":
        # Low admin willingness → avoid stabilize
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
        node_id=f"strat-root-{fid}-t{tick}",
        action_id=f"action-{mode}",
    )
    strategy = Strategy(
        id=f"strategy-{fid}-t{tick}",
        actor_id=fid,
        goal_id=goal.id,
        root_node_id=root_node.node_id,
        nodes=[root_node],
        projection_policy="symbolic_rule",
    )

    # Scale shift magnitudes by personality compatibility with mode
    # If faction's natural tendency already aligns with mode, dampen shifts
    # If misaligned, amplify shifts to correct course
    
    scale_factor = 1.0
    if mode == "stabilize":
        base_e, base_o, base_c, base_l, base_z = (
            behavior.engagement_threshold,
            behavior.objective_bias,
            behavior.concentration,
            behavior.liquidity_preference,
            behavior.centralization,
        )
        # Stabilize wants: low E, low O, low C, high L, high Z
        alignment = (1 - base_e) + (1 - base_o) + (1 - base_c) + base_l + base_z
        scale_factor = 1.0 - (alignment / 5.0 * 0.5)  # [-0.1, 0.5] range
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
        # Connect wants: low E, low O, low C, low L, medium Z
        alignment = (1 - base_e) + (1 - base_o) + (1 - base_c) + (1 - base_l) + (base_z * 0.5)
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
        # Expand wants: high E, high O, high C, low L, low Z
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
        # Reconcile wants: low E, medium O, low C, high L, low Z
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
    state: SimState,
    faction: Faction,
    perception: Optional[Perception] = None,
) -> None:
    """Compute and attach a fresh symbolic intent for the current tick."""
    snapshot = _symbolic_snapshot(state, faction, perception)
    faction.symbolic_intent = _build_goal_and_strategy(state, faction, snapshot)


def _grow_relations(state: SimState) -> None:
    """Apply base growth to all known faction relations, capped at 1.0."""
    rate = state.config.relation_growth_rate
    if rate <= 0.0:
        return
    for key, value in list(state.relations.items()):
        state.relations[key] = _clamp01(value + rate)


# --------------------------------------------------------------------------- #
# Logistics AI — route planning                                               #
# --------------------------------------------------------------------------- #


def _plan_moves(
    state: SimState,
    faction: Faction,
    perception: Optional[Perception] = None,
) -> None:
    """Decide how to route spice across links this tick.

    Gas-fee economics deliberately reward focused bulk shipments:
    - Each order pays a flat `transport_base_cost` overhead (burned from source)
      before any spice moves.  Ten scattered orders pay it ten times.
    - Orders that cannot cover the base cost are dropped entirely.
    - Additionally, a proportional `transport_gas_fee` destroys a fraction
      of what does move.  Both fees compound, so multi-hop routes are costly.

     Strategy with behavior matrix:
     1. Build offense scores and defense scores.
     2. Apply engagement threshold to offense participation.
     3. Mix offense/defense using objective_bias.
     4. Keep top-K targets based on concentration (high concentration => low K).
     5. Spend fraction based on liquidity_preference (high liquidity => spend less).
    """
    faction_id = faction.faction_id
    behavior = _effective_behavior(faction)
    owned = set(state.nodes_owned_by(faction_id))
    faction.move_orders = []

    if not owned:
        return

    # Collect target scores
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
    offense_scores: dict[str, float] = {}
    for nid in offense_targets:
        d = max(1, bfs.get(nid, 1))
        target_owner = state.nodes[nid].owner_id
        relation_factor = 1.0
        if target_owner is not None and target_owner != faction_id:
            state.know_each_other(faction_id, target_owner)
            relation_factor = _relation_pressure_factor(
                state,
                faction_id,
                target_owner,
            )
        offense_scores[nid] = (state.nodes[nid].spice_flow / d) * relation_factor

    # Normalize offense and apply engagement threshold.
    if offense_scores:
        max_off = max(offense_scores.values())
        if max_off > 0:
            for nid in list(offense_scores.keys()):
                normalized = offense_scores[nid] / max_off
                if normalized < behavior.engagement_threshold:
                    offense_scores[nid] = 0.0

    # Mix offense and defense into one target map using objective bias.
    # objective_bias=1 -> pure offense, objective_bias=0 -> pure defense.
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

    # Concentration axis: high => focus few targets, low => spread across many.
    target_count = max(1, round((1.0 - behavior.concentration) * len(ranked_targets)))
    selected_targets = ranked_targets[:target_count]

    # Liquidity axis: high => conserve reserves, low => spend aggressively.
    spend_fraction = state.config.max_spice_move_fraction * (
        1.0 - behavior.liquidity_preference
    )
    spend_fraction = max(0.05, min(1.0, spend_fraction))

    base_cost = state.config.transport_base_cost

    for src_index, src_id in enumerate(sorted(owned)):
        src_node = state.nodes[src_id]
        # Must have strictly more than the base cost to make any shipment worthwhile
        if src_node.spice_stock <= base_cost:
            continue

        max_dispatch = (src_node.spice_stock - base_cost) * spend_fraction

        # Distribute source intentions across selected targets.
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


def _plan_centralization(
    state: SimState,
    faction: Faction,
) -> None:
    """Plan administrative transport orders for drift suppression.

    The delivered spice is consumed later by the centralization pass, but the
    shipment itself must obey the same transport rules as any other order.
    """
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
    state: SimState,
    src: str,
    target: str,
    owned: set[str],
    faction_id: str,
) -> str | None:
    """Return the immediate neighbour of *src* on the shortest path to *target*.

    Routing is through owned nodes; the final hop may cross into unowned territory.
    """
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
    """Reset per-tick used_flow counters on all links."""
    for lnk in state.links.values():
        lnk.used_flow = 0.0
    state.admin_delivery_budget = {}


# --------------------------------------------------------------------------- #
# Logistics execution — move spice along ordered hops, apply fees            #
# --------------------------------------------------------------------------- #


def _execute_transport(state: SimState) -> None:
    """Apply all faction move orders with two-layer gas fee.

    For each order (src, dst, amount):
      1. Flat base cost (transport_base_cost) is burned from src first.
         If src doesn't have enough stock to cover base_cost + a meaningful
         amount, the order is skipped.
      2. Proportional fee (transport_gas_fee) is then applied to what remains.

    This structure makes scatter expensive and bulk movement efficient:
    - 10 orders of 1 unit each: pay base_cost x10
    - 1 order of 10 units: pay base_cost x1

    Delivery semantics:
    - Arrival at own node  → added to that node's spice_stock (reinforcement).
    - Arrival at enemy/neutral node → converted to conquest pressure.
    """
    base_cost = state.config.transport_base_cost
    gas_fee = state.config.transport_gas_fee

    for faction in state.active_factions():
        for src_id, dst_id, amount in faction.move_orders:
            src_node = state.nodes[src_id]
            dst_node = state.nodes[dst_id]

            # Enforce link capacity (authoritative clamp — planner may have pre-reserved,
            # but direct order injection in tests or future extensions must also be safe)
            link_key = (min(src_id, dst_id), max(src_id, dst_id))
            lnk = state.links.get(link_key)
            if lnk is not None:
                cap_available = max(0.0, lnk.max_flow - lnk.used_flow)
                amount = min(amount, cap_available)
                if amount <= 0:
                    continue
                lnk.used_flow += amount

            # Clamp to available stock
            total_required = base_cost + amount
            if src_node.spice_stock < total_required:
                # Reduce amount to what is left after base cost; skip if nothing remains
                amount = src_node.spice_stock - base_cost
                if amount <= 0:
                    # Still burn the base cost if we have any stock at all
                    burned = min(base_cost, src_node.spice_stock)
                    src_node.spice_stock -= burned
                    continue

            # Deduct base cost overhead (always burned, regardless of delivery)
            src_node.spice_stock -= base_cost
            # Deduct the shipment amount
            src_node.spice_stock -= amount
            src_node.spice_stock = max(0.0, src_node.spice_stock)

            # Apply proportional gas fee to the shipment
            delivered = amount * (1.0 - gas_fee)

            if dst_node.owner_id == faction.faction_id:
                # Friendly node — reinforcement
                dst_node.spice_stock += delivered
            else:
                # Enemy / neutral — convert delivery to conquest pressure
                fid = faction.faction_id
                dst_node.pressure.setdefault(fid, 0.0)
                dst_node.pressure[fid] += delivered
                dst_node.pressure_accumulated += delivered

                defender_id = dst_node.owner_id
                if defender_id is not None and defender_id != fid:
                    delta = -delivered * state.config.relation_pressure_impact
                    state.adjust_relation(fid, defender_id, delta)

                state.event_log.append(
                    f"[tick {state.tick}] {fid} delivered {delivered:.1f} pressure to"
                    f" {dst_id} (base_cost {base_cost:.1f} + gas {amount - delivered:.1f})"
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

            delivered = amount * (1.0 - gas_fee)
            dst_node.spice_stock += delivered
            state.admin_delivery_budget[dst_id] = (
                state.admin_delivery_budget.get(dst_id, 0.0) + delivered
            )
            state.event_log.append(
                f"[tick {state.tick}] ADMIN route: {faction.faction_id} delivered {delivered:.1f} spice to"
                f" {dst_id} (base_cost {base_cost:.1f} + gas {amount - delivered:.1f})"
            )


def _apply_conquest(state: SimState) -> list[str]:
    """Check nodes for ownership flips; handle spice seizure on conquest.

    Pressure on a node comes from spice explicitly routed there by _execute_transport.
    On a flip, any unallocated spice_stock on the node is seized and deposited into
    the conqueror's capital node.

    Returns list of node_ids that flipped ownership this tick.
    """
    flipped: list[str] = []

    for nid, node in state.nodes.items():
        if node.pressure_accumulated < state.config.flip_threshold:
            continue
        if not node.pressure:
            continue

        conqueror_id = max(node.pressure, key=lambda fid: node.pressure[fid])
        old_owner = node.owner_id

        if old_owner == conqueror_id:
            # Defender successfully reinforced — reset pressure
            node.pressure_accumulated = 0.0
            node.pressure = {}
            continue

        # --- Node flips ---
        seized = node.spice_stock  # unallocated spice seized by conqueror
        node.owner_id = conqueror_id
        node.pressure_accumulated = 0.0
        node.pressure = {}
        node.genome = state.factions[conqueror_id].genome[:]
        node.spice_stock = 0.0  # cleared; seized amount goes to capital

        cap_id = state.factions[conqueror_id].capital_id
        state.nodes[cap_id].spice_stock += seized

        flipped.append(nid)
        old_label = old_owner if old_owner else "neutral"
        state.event_log.append(
            f"[tick {state.tick}] Node {nid} flipped {old_label} \u2192 {conqueror_id}"
            + (f" (seized {seized:.1f} spice)" if seized > 0 else "")
        )

    return flipped


# --------------------------------------------------------------------------- #
# Spice income                                                                 #
# --------------------------------------------------------------------------- #


def _collect_income(state: SimState) -> None:
    """Add per-tick spice flow directly into each owned node's stock."""
    for nid, node in state.nodes.items():
        if node.owner_id is not None:
            node.spice_stock += node.spice_flow


# --------------------------------------------------------------------------- #
# Genome mutation and secession                                                #
# --------------------------------------------------------------------------- #


def _mutate_and_check_secession(state: SimState) -> list[str]:
    """Mutate node genomes with probability weighted by distance from capital.

    If any node's Hamming distance from its faction genome exceeds
    config.drift_threshold_bits, that node secedes into a new faction.

    Returns list of new faction_ids created this tick.
    """
    new_faction_ids: list[str] = []

    for faction in list(state.active_factions()):
        owned = state.nodes_owned_by(faction.faction_id)
        if not owned:
            continue
        bfs = _bfs_distances_state(state, faction.capital_id)

        for nid in owned:
            node = state.nodes[nid]
            depth = bfs.get(nid, 1)
            if depth < 0:
                depth = len(state.nodes)  # disconnected from capital — max drift

            # Mutation probability weighted by distance
            # P(mutate) = mutation_rate * (1 + depth) / (1 + max_depth_approx)
            # Simplified: P = min(1.0, mutation_rate * (depth + 1))
            p_mutate = min(1.0, state.config.mutation_rate * (depth + 1))
            if state._rng.random() < p_mutate:
                node.genome = _mutate_genome(node.genome, state._rng)

            _apply_centralization(state, faction, node)

            # Check secession
            hamming = _hamming_distance(node.genome, faction.genome)
            if hamming >= state.config.drift_threshold_bits:
                new_fid = _secede(state, nid, faction)
                new_faction_ids.append(new_fid)
                # Node is no longer in this faction — don't double-process
                # (loop continues over snapshot, ownership changed)

    return new_faction_ids


def _secede(state: SimState, node_id: str, parent_faction: Faction) -> str:
    """Break *node_id* off into a brand-new faction.

    The new faction:
    - Inherits the node's drifted genome as its own genome
    - Starts with the seceding node as its capital
    - Receives a small spice stock gift (the node's spice flow per tick)
    """
    new_fid = f"faction-{len(state.factions)}"
    # Ensure unique id
    while new_fid in state.factions:
        new_fid += "x"

    node = state.nodes[node_id]
    new_genome = node.genome[:]

    new_faction = Faction(
        faction_id=new_fid,
        capital_id=node_id,
        genome=new_genome,
        behavior=_genome_to_ecloz(new_genome),
        color=_genome_to_color(new_genome),
    )
    state.factions[new_fid] = new_faction
    node.owner_id = new_fid

    # Add Space + Actor to the World layer
    try:
        from ometeotl_core.model.actors import Actor

        actor = Actor(id=new_fid)
        actor.label = f"Faction {new_fid}"
        state.world.register_object(actor)
    except Exception:
        pass  # World layer enrichment is best-effort

    state.event_log.append(
        f"[tick {state.tick}] SECESSION: node {node_id} broke from {parent_faction.faction_id} → new faction {new_fid}"
    )
    return new_fid


# --------------------------------------------------------------------------- #
# Victory check                                                                #
# --------------------------------------------------------------------------- #


def _check_victory(state: SimState) -> None:
    """Set state.game_over and state.winner_id if a win condition is met."""
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
        # Winner by most nodes
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
    """Return connected components from current runtime links."""
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
    """Add a new undirected link to graph and ontology layers."""
    if a == b:
        return False
    key = (min(a, b), max(a, b))
    if key in state.links:
        return False

    state.links[key] = Link(source_id=key[0], target_id=key[1], max_flow=capacity)
    rel = SpaceRelation(source_space_id=key[0], target_space_id=key[1], relation_type="adjacent_to")
    state.relation_graph.add_relation(rel)
    state.world.space_relation_graph.add_relation(rel)
    return True


def _apply_globalization(state: SimState) -> None:
    """Rarely evolve transport topology and capacities.

    Per tick, at most one event can happen:
    - Existing link capacity grows by +1, or
    - A new 1-capacity bridge appears between disconnected components.
    """
    growth_p = state.config.globalization_link_growth_chance
    bridge_p = state.config.globalization_bridge_spawn_chance
    roll = state._rng.random()

    if roll < growth_p and state.links:
        key = state._rng.choice(list(state.links.keys()))
        lnk = state.links[key]
        lnk.max_flow += 1.0
        state.event_log.append(
            f"[tick {state.tick}] GLOBALIZATION: link {key[0]}-{key[1]} capacity +1 → {lnk.max_flow:.1f}"
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
            f"[tick {state.tick}] GLOBALIZATION: new bridge {min(a, b)}-{max(a, b)} created (cap 1.0)"
        )


# --------------------------------------------------------------------------- #
# Main tick step (with perception integration)                                #
# --------------------------------------------------------------------------- #


def step(state: SimState) -> None:
    """Advance the simulation by one tick.

    Order:
    1. Reset link usage counters
    2. Collect spice income into nodes
    3. Apply rare globalization event (link growth or bridge creation)
    4. Plan AI move orders (perception-aware)
    5. Execute transport: move spice, apply base cost + proportional gas fee
    6. Apply conquest (check flips, seize unallocated spice)
    7. Mutate genomes and check secession
    8. Check victory conditions
    9. Increment tick counter
    """
    if state.game_over:
        return

    _reset_link_usage(state)
    _collect_income(state)
    _apply_globalization(state)

    for faction in state.active_factions():
        perception = None
        if state.config.perception_mode == "limited":
            perception = get_faction_perception(state, faction.faction_id)
        _run_symbolic_deliberation(state, faction, perception)
        _plan_moves(state, faction, perception)
        _plan_centralization(state, faction)

    _execute_transport(state)
    _apply_conquest(state)
    _grow_relations(state)
    _mutate_and_check_secession(state)
    _check_victory(state)

    state.tick += 1


# --------------------------------------------------------------------------- #
# Initialisation                                                               #
# --------------------------------------------------------------------------- #


def create_sim(config: SimConfig) -> SimState:
    """Build a fresh SimState from *config*.

    Steps:
    1. Generate a random graph
    2. Build the Ometeotl World + SpaceRelationGraph
    3. Build Link objects with random capacities in [min_link_flow, max_link_flow]
    4. Randomly assign starting capitals (one per faction)
    5. Initialise factions with random genomes
    6. Initialise nodes — owned capitals, all others neutral
    7. Seed node spice stocks to config.initial_node_spice
    """
    config.validate()
    rng = random.Random(config.seed)
    raw = build_graph(config)

    # ---- Ometeotl world layer ----
    world = World(id="lab10-complex-behavior-sim-world")
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

    # ---- Pick capital nodes ----
    node_ids = raw.all_node_ids()
    rng.shuffle(node_ids)
    capital_ids = node_ids[: config.num_factions]

    # ---- Build factions ----
    from ometeotl_core.model.actors import Actor

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

        actor = Actor(id=fid)
        actor.label = f"Faction {i}"
        world.register_object(actor)

    # ---- Build nodes ----
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

        nodes[nid] = Node(
            node_id=nid,
            spice_flow=raw_node.spice_flow,
            x=raw_node.x,
            y=raw_node.y,
            owner_id=owner,
            genome=genome,
            spice_stock=config.initial_node_spice,
        )

    state = SimState(
        config=config,
        world=world,
        relation_graph=relation_graph,
        nodes=nodes,
        factions=factions,
        links=links,
    )
    state._rng = random.Random(rng.randint(0, 2**32 - 1))

    state.event_log.append(
        f"[tick 0] Simulation started (Lab 10 - Complex Behavior). "
        f"{config.num_factions} factions, {config.num_nodes} nodes, "
        f"perception_mode={config.perception_mode}, "
        f"base_cost={config.transport_base_cost}, gas_fee={config.transport_gas_fee}, "
        f"admin_cost={config.centralization_admin_cost}, "
        f"relation_initial={config.relation_initial}, "
        f"relation_growth={config.relation_growth_rate}, "
        f"g_link={config.globalization_link_growth_chance}, "
        f"g_bridge={config.globalization_bridge_spawn_chance}."
    )
    return state


# --------------------------------------------------------------------------- #
# Serialisation                                                                #
# --------------------------------------------------------------------------- #


def serialize_state(state: SimState) -> dict:
    """Return a JSON-compatible dict for the web UI."""
    factions_out = {}
    for fid, faction in state.factions.items():
        owned = state.nodes_owned_by(fid)
        factions_out[fid] = {
            "faction_id": fid,
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
        }

    nodes_out = []
    for nid, node in state.nodes.items():
        nodes_out.append(
            {
                "node_id": nid,
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
        {
            "a": a,
            "b": b,
            "value": round(value, 3),
        }
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
        "event_log": state.event_log[-20:],
        "config": state.config.to_dict(),
    }
