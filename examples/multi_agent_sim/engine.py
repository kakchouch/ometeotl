"""Core simulation engine for the multi-agent graph simulation.

Responsibilities (domain layer — stays in examples):
- SimState: full mutable simulation state
- Node: per-node runtime state (owner, pressure, genome copy)
- Faction: faction runtime state (stock, genome, capital, AI priorities)
- Genome operations: hamming distance, random bit flip with BFS-depth weighting
- Conquest: resource pressure application and node flip logic
- Symbolic AI: priority scoring for border nodes (full information)
- Secession: genome drift detection, new faction bootstrapping
- Tick step: orchestrates all of the above in the correct order
- Serialisation: produces a flat JSON-compatible dict for the web UI

Ometeotl is used for the ontological / relational graph layer:
  World + Space (nodes) + SpaceRelation (adjacency) + SpaceRelationGraph
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field

from ometeotl_core.model.spaces import Space
from ometeotl_core.model.space_relations import SpaceRelation, SpaceRelationGraph
from ometeotl_core.model.world import World

from .config import SimConfig
from .graph_gen import RawGraph, build_graph, bfs_distances


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


# --------------------------------------------------------------------------- #
# Data types                                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class Node:
    """Runtime state for one graph node."""

    node_id: str
    spice_flow: int
    x: float  # UI position, normalised [0..1]
    y: float
    owner_id: str | None  # faction id or None (neutral)
    genome: list[int]  # node's local genome copy (all zeros for neutral)
    # Cumulative pressure applied this turn by each attacker: {faction_id: pressure}
    pressure: dict[str, float] = field(default_factory=dict)
    # Total lifetime pressure needed to flip the node (resets on flip)
    pressure_accumulated: float = 0.0


@dataclass
class Faction:
    """Runtime state for one faction."""

    faction_id: str
    capital_id: str
    genome: list[int]
    spice_stock: float = 0.0
    color: str = "#888888"  # hex color for the UI, assigned at creation
    # Priority weights per border node: {node_id: weight} — recomputed each tick
    priorities: dict[str, float] = field(default_factory=dict)
    is_eliminated: bool = False


@dataclass
class SimState:
    """Full mutable runtime state of the simulation."""

    config: SimConfig
    world: World
    relation_graph: SpaceRelationGraph
    nodes: dict[str, Node]          # node_id → Node
    factions: dict[str, Faction]    # faction_id → Faction
    tick: int = 0
    game_over: bool = False
    winner_id: str | None = None
    event_log: list[str] = field(default_factory=list)
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
        return sum(self.nodes[nid].spice_flow for nid in self.nodes_owned_by(faction_id))

    def active_factions(self) -> list[Faction]:
        return [f for f in self.factions.values() if not f.is_eliminated]


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


# --------------------------------------------------------------------------- #
# Symbolic AI — priority assignment                                            #
# --------------------------------------------------------------------------- #


def _assign_priorities(state: SimState, faction: Faction) -> None:
    """Score each node (offensive + defensive) and allocate spice resources.

    Offensive targets (border nodes):
      score = node.spice_flow / (bfs_distance + 1)
      Rewards attacking valuable, nearby unowned neighbors.

    Defensive targets (owned nodes under threat):
      score = pressure_accumulated * (1 + node.spice_flow)
      Prioritizes defending nodes closest to flipping and highest-income nodes.

    Resources are allocated proportionally to combined offensive + defensive needs.
    """
    faction_id = faction.faction_id
    owned = set(state.nodes_owned_by(faction_id))

    # Collect offensive targets (unowned neighbors)
    offense_targets = state.border_targets_for(faction_id)

    # Collect defensive targets (owned nodes with accumulated pressure from enemies)
    defense_targets: dict[str, float] = {}
    for nid in owned:
        node = state.nodes[nid]
        if node.pressure_accumulated > 0:
            # Defensive priority = threat level weighted by node value
            # Nodes close to flipping with high income get priority
            threat_score = node.pressure_accumulated * (1.0 + node.spice_flow)
            defense_targets[nid] = threat_score

    # Score both offensive and defensive allocations
    bfs = _bfs_distances_state(state, faction.capital_id)
    raw: dict[str, float] = {}

    # Offensive: profit from conquest
    for nid in offense_targets:
        d = bfs.get(nid, -1)
        if d <= 0:
            d = 1  # capital's direct neighbour or unreachable � treat as dist 1
        raw[nid] = state.nodes[nid].spice_flow / d

    # Defensive: threat mitigation
    raw.update(defense_targets)

    if not raw:
        faction.priorities = {}
        return

    total = sum(raw.values())
    if total == 0:
        faction.priorities = {nid: 1.0 / len(raw) for nid in raw}
    else:
        faction.priorities = {nid: v / total for nid, v in raw.items()}


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


# --------------------------------------------------------------------------- #
# Data types                                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class Node:
    """Runtime state for one graph node."""

    node_id: str
    spice_flow: int
    x: float  # UI position, normalised [0..1]
    y: float
    owner_id: str | None  # faction id or None (neutral)
    genome: list[int]  # node's local genome copy (all zeros for neutral)
    # Cumulative pressure applied this turn by each attacker: {faction_id: pressure}
    pressure: dict[str, float] = field(default_factory=dict)
    # Total lifetime pressure needed to flip the node (resets on flip)
    pressure_accumulated: float = 0.0


@dataclass
class Faction:
    """Runtime state for one faction."""

    faction_id: str
    capital_id: str
    genome: list[int]
    spice_stock: float = 0.0
    color: str = "#888888"  # hex color for the UI, assigned at creation
    # Priority weights per border node: {node_id: weight} — recomputed each tick
    priorities: dict[str, float] = field(default_factory=dict)
    is_eliminated: bool = False


@dataclass
class SimState:
    """Full mutable runtime state of the simulation."""

    config: SimConfig
    world: World
    relation_graph: SpaceRelationGraph
    nodes: dict[str, Node]          # node_id → Node
    factions: dict[str, Faction]    # faction_id → Faction
    tick: int = 0
    game_over: bool = False
    winner_id: str | None = None
    event_log: list[str] = field(default_factory=list)
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
        return sum(self.nodes[nid].spice_flow for nid in self.nodes_owned_by(faction_id))

    def active_factions(self) -> list[Faction]:
        return [f for f in self.factions.values() if not f.is_eliminated]


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


# --------------------------------------------------------------------------- #
# Symbolic AI — priority assignment                                            #
# --------------------------------------------------------------------------- #


def _assign_priorities(state: SimState, faction: Faction) -> None:
    """Score each node (offensive + defensive) and allocate spice resources.

    Offensive targets (border nodes):
      score = node.spice_flow / (bfs_distance + 1)
      Rewards attacking valuable, nearby unowned neighbors.

    Defensive targets (owned nodes under threat):
      score = pressure_accumulated * (1 + node.spice_flow)
      Prioritizes defending nodes closest to flipping and highest-income nodes.

    Resources are allocated proportionally to combined offensive + defensive needs.
    """
    faction_id = faction.faction_id
    owned = set(state.nodes_owned_by(faction_id))

    # Collect offensive targets (unowned neighbors)
    offense_targets = state.border_targets_for(faction_id)

    # Collect defensive targets (owned nodes with accumulated pressure from enemies)
    defense_targets: dict[str, float] = {}
    for nid in owned:
        node = state.nodes[nid]
        if node.pressure_accumulated > 0:
            # Defensive priority = threat level weighted by node value
            # Nodes close to flipping with high income get priority
            threat_score = node.pressure_accumulated * (1.0 + node.spice_flow)
            defense_targets[nid] = threat_score

    # Score both offensive and defensive allocations
    bfs = _bfs_distances_state(state, faction.capital_id)
    raw: dict[str, float] = {}

    # Offensive: profit from conquest
    for nid in offense_targets:
        d = bfs.get(nid, -1)
        if d <= 0:
            d = 1  # capital's direct neighbour or unreachable � treat as dist 1
        raw[nid] = state.nodes[nid].spice_flow / d

    # Defensive: threat mitigation
    raw.update(defense_targets)

    if not raw:
        faction.priorities = {}
        return

    total = sum(raw.values())
    if total == 0:
        faction.priorities = {nid: 1.0 / len(raw) for nid in raw}
    else:
        faction.priorities = {nid: v / total for nid, v in raw.items()}


# --------------------------------------------------------------------------- #
# Conquest                                                                     #
# --------------------------------------------------------------------------- #


def _apply_conquest(state: SimState) -> list[str]:
    """Each faction spends its spice stock applying pressure to border nodes.

    Returns list of node_ids that flipped ownership this tick.
    """
    flipped: list[str] = []

    for faction in state.active_factions():
        if not faction.priorities:
            continue
        budget = faction.spice_stock
        for nid, weight in faction.priorities.items():
            spend = budget * weight
            node = state.nodes[nid]
            if faction.faction_id not in node.pressure:
                node.pressure[faction.faction_id] = 0.0
            node.pressure[faction.faction_id] += spend
            node.pressure_accumulated += spend
            faction.spice_stock -= spend

        faction.spice_stock = max(0.0, faction.spice_stock)

    # Check flips
    for nid, node in state.nodes.items():
        if node.pressure_accumulated >= state.config.flip_threshold:
            # Find the faction that applied the most total pressure this accumulation
            if not node.pressure:
                continue
            conqueror_id = max(node.pressure, key=lambda fid: node.pressure[fid])
            old_owner = node.owner_id
            if old_owner == conqueror_id:
                # Already owner — just reset pressure (reinforcement)
                node.pressure_accumulated = 0.0
                node.pressure = {}
                continue

            node.owner_id = conqueror_id
            node.pressure_accumulated = 0.0
            node.pressure = {}
            # Inherit conqueror's genome
            node.genome = state.factions[conqueror_id].genome[:]
            flipped.append(nid)

            old_label = old_owner if old_owner else "neutral"
            state.event_log.append(
                f"[tick {state.tick}] Node {nid} flipped from {old_label} to {conqueror_id}"
            )

    return flipped


# --------------------------------------------------------------------------- #
# Spice income                                                                 #
# --------------------------------------------------------------------------- #


def _collect_income(state: SimState) -> None:
    """Add each faction's per-tick spice income to its stock."""
    for faction in state.active_factions():
        faction.spice_stock += state.spice_income_for(faction.faction_id)


# --------------------------------------------------------------------------- #
# Genome mutation and secession                                                #
# --------------------------------------------------------------------------- #


def _mutate_and_check_secession(state: SimState) -> list[str]:
    """Mutate node genomes with probability weighted by distance from capital.

    If any node's Hamming distance from its faction genome exceeds
    config.drift_threshold_bits, that node seceeds into a new faction.

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
    - Receives a small spice stock gift (half the node's spice flow per tick)
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
        spice_stock=float(node.spice_flow),
        color=_next_color(),
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
        best = max(state.active_factions(), key=lambda f: len(state.nodes_owned_by(f.faction_id)))
        state.game_over = True
        state.winner_id = best.faction_id
        state.event_log.append(
            f"[tick {state.tick}] Max ticks reached. Winner: {best.faction_id}"
        )


# --------------------------------------------------------------------------- #
# Main tick step                                                                #
# --------------------------------------------------------------------------- #


def step(state: SimState) -> None:
    """Advance the simulation by one tick.

    Order:
    1. Collect spice income
    2. Assign AI priorities (symbolic AI, full information)
    3. Apply conquest pressure
    4. Mutate node genomes and check secession
    5. Check victory conditions
    6. Increment tick counter
    """
    if state.game_over:
        return

    _collect_income(state)

    for faction in state.active_factions():
        _assign_priorities(state, faction)

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
    3. Randomly assign starting capitals (one per faction)
    4. Initialise factions with random genomes
    5. Initialise nodes — all neutral except capital nodes
    """
    config.validate()
    _reset_color_index()

    rng = random.Random(config.seed)

    raw = build_graph(config)

    # ---- Ometeotl world layer ----
    world = World(id="multi-agent-sim-world")
    relation_graph = SpaceRelationGraph()

    for raw_node in raw.nodes:
        space = Space(id=raw_node.node_id)
        space.label = raw_node.node_id
        world.add_space(space)

    for a, b in raw.edges:
        relation_graph.add_relation(
            SpaceRelation(source_space_id=a, target_space_id=b, relation_type="adjacent_to")
        )

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
            spice_stock=0.0,
            color=_next_color(),
        )
        factions[fid] = faction

        actor = Actor(id=fid)
        actor.label = f"Faction {i}"
        world.register_object(actor)

    # ---- Build nodes ----
    capital_to_faction: dict[str, str] = {f.capital_id: fid for fid, f in factions.items()}
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
        )

    state = SimState(
        config=config,
        world=world,
        relation_graph=relation_graph,
        nodes=nodes,
        factions=factions,
    )
    state._rng = random.Random(rng.randint(0, 2**32 - 1))

    state.event_log.append(f"[tick 0] Simulation started. {config.num_factions} factions, {config.num_nodes} nodes.")
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
            "spice_stock": round(faction.spice_stock, 2),
            "spice_income": state.spice_income_for(fid),
            "node_count": len(owned),
            "is_eliminated": faction.is_eliminated,
            "priorities": faction.priorities,
        }

    nodes_out = []
    for nid, node in state.nodes.items():
        nodes_out.append({
            "node_id": nid,
            "spice_flow": node.spice_flow,
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
        })

    edges_out = [
        {"a": r.source_space_id, "b": r.target_space_id}
        for r in state.relation_graph.relations
        if r.relation_type == "adjacent_to"
    ]

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
