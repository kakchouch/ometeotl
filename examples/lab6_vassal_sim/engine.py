"""Core simulation engine for Lab 5 — Behavior Logistics Simulation.

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

import random
from dataclasses import dataclass, field
from typing import Optional

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


def _clamp255(value: int) -> int:
    return max(0, min(255, value))


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    if len(value) != 6:
        return (136, 136, 136)
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        return (136, 136, 136)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        _clamp255(rgb[0]),
        _clamp255(rgb[1]),
        _clamp255(rgb[2]),
    )


def _derive_child_color(parent_color: str, rng: random.Random) -> str:
    """Return a close color variant to preserve lineage readability."""
    pr, pg, pb = _hex_to_rgb(parent_color)
    return _rgb_to_hex(
        (
            pr + rng.randint(-28, 28),
            pg + rng.randint(-28, 28),
            pb + rng.randint(-28, 28),
        )
    )


def _drift_behavior(
    behavior: BehaviorProfile,
    rng: random.Random,
    magnitude: float,
) -> BehaviorProfile:
    """Return a drifted behavior profile (small bounded random walk in [0, 1])."""
    mag = max(0.0, magnitude)
    return BehaviorProfile(
        engagement_threshold=_clamp01(
            behavior.engagement_threshold + rng.uniform(-mag, mag)
        ),
        concentration=_clamp01(behavior.concentration + rng.uniform(-mag, mag)),
        liquidity_preference=_clamp01(
            behavior.liquidity_preference + rng.uniform(-mag, mag)
        ),
        objective_bias=_clamp01(behavior.objective_bias + rng.uniform(-mag, mag)),
    )


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
    """

    engagement_threshold: float
    concentration: float
    liquidity_preference: float
    objective_bias: float


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
    parent_faction_id: str | None = None
    top_ancestor_id: str = ""
    hierarchy_depth: int = 0
    # Move orders planned this tick: list of (from_node, to_node, amount)
    move_orders: list[tuple[str, str, float]] = field(default_factory=list)
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
    _rng: random.Random = field(default_factory=random.Random, repr=False)
    vassal_counters: dict[str, int] = field(default_factory=dict)

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
                nb_owner = self.nodes[nb].owner_id
                if nb_owner is None:
                    targets.add(nb)
                    continue
                if not self.are_allied(faction_id, nb_owner):
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

    def top_ancestor_of(self, faction_id: str) -> str:
        faction = self.factions.get(faction_id)
        if faction is None:
            return faction_id
        top = faction.top_ancestor_id or faction.faction_id
        if top not in self.factions:
            return faction.faction_id
        return top

    def are_allied(self, a: str | None, b: str | None) -> bool:
        if a is None or b is None:
            return False
        return self.top_ancestor_of(a) == self.top_ancestor_of(b)


# --------------------------------------------------------------------------- #
# Colour palette for factions                                                  #
# --------------------------------------------------------------------------- #

_FACTION_COLORS = [
    "#e63946",  # red
    "#457b9d",  # blue
    "#2a9d8f",  # teal
    "#f4a261",  # orange
    "#8338ec",  # violet
    "#ffbe0b",  # amber
    "#06d6a0",  # green
    "#fb5607",  # burnt orange
    "#3a86ff",  # sky blue
    "#ff006e",  # pink
    "#8ecae6",  # light blue
    "#95d5b2",  # light green
]
_color_index = 0


def _next_color() -> str:
    global _color_index
    color = _FACTION_COLORS[_color_index % len(_FACTION_COLORS)]
    _color_index += 1
    return color


def _reset_color_index() -> None:
    global _color_index
    _color_index = 0


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


def _random_behavior(config: SimConfig, rng: random.Random) -> BehaviorProfile:
    """Sample a behavior profile from configured ranges."""
    return BehaviorProfile(
        engagement_threshold=rng.uniform(
            config.behavior_engagement_min,
            config.behavior_engagement_max,
        ),
        concentration=rng.uniform(
            config.behavior_concentration_min,
            config.behavior_concentration_max,
        ),
        liquidity_preference=rng.uniform(
            config.behavior_liquidity_min,
            config.behavior_liquidity_max,
        ),
        objective_bias=rng.uniform(
            config.behavior_objective_min,
            config.behavior_objective_max,
        ),
    )


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
    behavior = faction.behavior
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

    bfs = _bfs_distances_state(state, faction.capital_id)
    offense_scores: dict[str, float] = {}
    for nid in offense_targets:
        d = max(1, bfs.get(nid, 1))
        offense_scores[nid] = state.nodes[nid].spice_flow / d

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

            if dst_node.owner_id == faction.faction_id or state.are_allied(
                faction.faction_id, dst_node.owner_id
            ):
                # Friendly node — reinforcement
                dst_node.spice_stock += delivered
            else:
                # Enemy / neutral — convert delivery to conquest pressure
                fid = faction.faction_id
                dst_node.pressure.setdefault(fid, 0.0)
                dst_node.pressure[fid] += delivered
                dst_node.pressure_accumulated += delivered
                state.event_log.append(
                    f"[tick {state.tick}] {fid} delivered {delivered:.1f} pressure to"
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

        if old_owner is not None and state.are_allied(conqueror_id, old_owner):
            # Internal hierarchy pressure should not trigger a territorial flip.
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


def _apply_vassal_tribute(state: SimState) -> None:
    """Transfer a fraction of vassal capital stock to its direct parent capital."""
    tribute_frac = state.config.vassal_tribute_fraction
    if tribute_frac <= 0:
        return

    for faction in state.active_factions():
        parent_id = faction.parent_faction_id
        if parent_id is None or parent_id not in state.factions:
            continue
        if faction.capital_id not in state.nodes:
            continue
        parent_capital = state.factions[parent_id].capital_id
        if parent_capital not in state.nodes:
            continue

        source_node = state.nodes[faction.capital_id]
        target_node = state.nodes[parent_capital]
        tribute = source_node.spice_stock * tribute_frac
        if tribute <= 0:
            continue

        source_node.spice_stock -= tribute
        target_node.spice_stock += tribute
        state.event_log.append(
            f"[tick {state.tick}] TRIBUTE: {faction.faction_id} -> {parent_id} "
            f"({tribute:.1f} spice)"
        )


# --------------------------------------------------------------------------- #
# Genome mutation and secession                                                #
# --------------------------------------------------------------------------- #


def _mutate_and_check_secession(state: SimState) -> list[str]:
    """Mutate node genomes and trigger vassal autonomy or full secession.

    Rules:
    - If node drift from local faction genome reaches drift_threshold_bits,
      autonomy is triggered.
    - If drift from top ancestor genome also reaches top_secession_threshold_bits,
      the node becomes fully independent.
    - Otherwise, the node forms a vassal under its direct parent faction.
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
                depth = len(state.nodes)

            p_mutate = min(1.0, state.config.mutation_rate * (depth + 1))
            if state._rng.random() < p_mutate:
                node.genome = _mutate_genome(node.genome, state._rng)
                drift_mag = min(0.2, 0.02 + 0.03 * min(depth, 5))
                faction.behavior = _drift_behavior(
                    faction.behavior,
                    state._rng,
                    drift_mag,
                )

            top_id = state.top_ancestor_of(faction.faction_id)
            top_genome = (
                state.factions[top_id].genome
                if top_id in state.factions
                else faction.genome
            )

            hamming_parent = _hamming_distance(node.genome, faction.genome)
            hamming_top = _hamming_distance(node.genome, top_genome)

            if hamming_parent >= state.config.drift_threshold_bits:
                if hamming_top >= state.config.top_secession_threshold_bits:
                    new_fid = _secede_independent(state, nid, faction)
                else:
                    new_fid = _secede_as_vassal(state, nid, faction)
                new_faction_ids.append(new_fid)

    return new_faction_ids


def _next_vassal_faction_id(state: SimState, parent_id: str) -> str:
    index = state.vassal_counters.get(parent_id, 0) + 1
    state.vassal_counters[parent_id] = index
    candidate = f"{parent_id}.v{index}"
    while candidate in state.factions:
        index += 1
        state.vassal_counters[parent_id] = index
        candidate = f"{parent_id}.v{index}"
    return candidate


def _register_actor_for_faction(
    state: SimState, faction: Faction, actor_label: str
) -> None:
    try:
        from ometeotl_core.model.actors import Actor

        actor = Actor(id=faction.faction_id)
        actor.label = actor_label
        actor.attributes["hierarchy_depth"] = faction.hierarchy_depth
        actor.attributes["top_ancestor_id"] = faction.top_ancestor_id
        if faction.parent_faction_id is not None:
            actor.attributes["parent_faction_id"] = faction.parent_faction_id

        state.world.register_object(actor)

        if faction.parent_faction_id is not None:
            parent_obj = state.world.model_registry.get(faction.parent_faction_id)
            if isinstance(parent_obj, Actor):
                if parent_obj.composition_mode != "composite":
                    parent_obj.composition_mode = "composite"
                if faction.faction_id not in parent_obj.get_components():
                    parent_obj.add_component(faction.faction_id)
    except Exception:
        pass


def _secede_as_vassal(state: SimState, node_id: str, parent_faction: Faction) -> str:
    """Create a vassal faction under *parent_faction* from *node_id*."""
    new_fid = _next_vassal_faction_id(state, parent_faction.faction_id)

    node = state.nodes[node_id]
    inherited_behavior = _drift_behavior(parent_faction.behavior, state._rng, 0.12)
    new_faction = Faction(
        faction_id=new_fid,
        capital_id=node_id,
        genome=node.genome[:],
        behavior=inherited_behavior,
        color=_derive_child_color(parent_faction.color, state._rng),
        parent_faction_id=parent_faction.faction_id,
        top_ancestor_id=state.top_ancestor_of(parent_faction.faction_id),
        hierarchy_depth=parent_faction.hierarchy_depth + 1,
    )
    state.factions[new_fid] = new_faction
    node.owner_id = new_fid

    _register_actor_for_faction(
        state,
        new_faction,
        actor_label=f"Vassal of {parent_faction.faction_id}",
    )

    state.event_log.append(
        f"[tick {state.tick}] AUTONOMY: node {node_id} from {parent_faction.faction_id} "
        f"formed vassal {new_fid}"
    )
    return new_fid


def _secede_independent(state: SimState, node_id: str, parent_faction: Faction) -> str:
    """Break *node_id* off into a new independent root faction."""
    new_fid = f"faction-{len(state.factions)}"
    while new_fid in state.factions:
        new_fid += "x"

    node = state.nodes[node_id]
    inherited_behavior = _drift_behavior(parent_faction.behavior, state._rng, 0.12)

    new_faction = Faction(
        faction_id=new_fid,
        capital_id=node_id,
        genome=node.genome[:],
        behavior=inherited_behavior,
        color=_next_color(),
        parent_faction_id=None,
        top_ancestor_id=new_fid,
        hierarchy_depth=0,
    )
    state.factions[new_fid] = new_faction
    node.owner_id = new_fid

    _register_actor_for_faction(state, new_faction, actor_label=f"Faction {new_fid}")

    state.event_log.append(
        f"[tick {state.tick}] SECESSION: node {node_id} broke from "
        f"{parent_faction.faction_id} -> independent faction {new_fid}"
    )
    return new_fid


# --------------------------------------------------------------------------- #
# Victory check                                                                #
# --------------------------------------------------------------------------- #


def _check_victory(state: SimState) -> None:
    """Set state.game_over and state.winner_id if a win condition is met."""
    total = len(state.nodes)
    coalition_counts: dict[str, int] = {}
    for node in state.nodes.values():
        if node.owner_id is None:
            continue
        top_id = state.top_ancestor_of(node.owner_id)
        coalition_counts[top_id] = coalition_counts.get(top_id, 0) + 1

    for top_id, owned in coalition_counts.items():
        if owned == total:
            state.game_over = True
            state.winner_id = top_id
            state.event_log.append(
                f"[tick {state.tick}] hierarchy led by {top_id} controls all nodes — VICTORY"
            )
            return

    if state.config.max_ticks > 0 and state.tick >= state.config.max_ticks:
        if not coalition_counts:
            return
        # Winner by coalition node count.
        best_top = max(coalition_counts.items(), key=lambda kv: kv[1])[0]
        state.game_over = True
        state.winner_id = best_top
        state.event_log.append(
            f"[tick {state.tick}] Max ticks reached. Winner hierarchy: {best_top}"
        )


# --------------------------------------------------------------------------- #
# Main tick step (with perception integration)                                #
# --------------------------------------------------------------------------- #


def step(state: SimState) -> None:
    """Advance the simulation by one tick.

    Order:
    1. Reset link usage counters
    2. Collect spice income into nodes
    3. Plan AI move orders (perception-aware)
    4. Execute transport: move spice, apply base cost + proportional gas fee
    5. Apply conquest (check flips, seize unallocated spice)
    6. Mutate genomes and check secession
    7. Check victory conditions
    8. Increment tick counter
    """
    if state.game_over:
        return

    _reset_link_usage(state)
    _collect_income(state)
    _apply_vassal_tribute(state)

    for faction in state.active_factions():
        perception = None
        if state.config.perception_mode == "limited":
            perception = get_faction_perception(state, faction.faction_id)
        _plan_moves(state, faction, perception)

    _execute_transport(state)
    _apply_conquest(state)
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
    _reset_color_index()

    rng = random.Random(config.seed)
    raw = build_graph(config)

    # ---- Ometeotl world layer ----
    world = World(id="lab6-vassal-sim-world")
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
            behavior=_random_behavior(config, rng),
            color=_next_color(),
            parent_faction_id=None,
            top_ancestor_id=fid,
            hierarchy_depth=0,
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
        f"[tick 0] Simulation started (Lab 6 - Vassal Logistics). "
        f"{config.num_factions} factions, {config.num_nodes} nodes, "
        f"perception_mode={config.perception_mode}, "
        f"base_cost={config.transport_base_cost}, gas_fee={config.transport_gas_fee}, "
        f"autonomy_bits={config.drift_threshold_bits}, "
        f"top_secession_bits={config.top_secession_threshold_bits}."
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
            "parent_faction_id": faction.parent_faction_id,
            "top_ancestor_id": faction.top_ancestor_id,
            "hierarchy_depth": faction.hierarchy_depth,
            "is_vassal": faction.parent_faction_id is not None,
            "genome": faction.genome,
            "genome_str": "".join(str(b) for b in faction.genome),
            "behavior": {
                "engagement_threshold": round(faction.behavior.engagement_threshold, 3),
                "concentration": round(faction.behavior.concentration, 3),
                "liquidity_preference": round(faction.behavior.liquidity_preference, 3),
                "objective_bias": round(faction.behavior.objective_bias, 3),
            },
            "total_spice": round(state.total_spice_for(fid), 2),
            "spice_income": state.spice_income_for(fid),
            "node_count": len(owned),
            "is_eliminated": faction.is_eliminated,
            "move_orders": [
                {"from": s, "to": d, "amount": round(a, 2)}
                for s, d, a in faction.move_orders
            ],
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

    return {
        "tick": state.tick,
        "game_over": state.game_over,
        "winner_id": state.winner_id,
        "factions": factions_out,
        "nodes": nodes_out,
        "edges": edges_out,
        "event_log": state.event_log[-20:],
        "config": state.config.to_dict(),
    }
