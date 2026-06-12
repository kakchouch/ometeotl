"""Engine for the Spatial Map Lab.

Exercises the ometeotl_foundations.spatial layer end-to-end:
  - GeometricSpace[BoundingBox] for a grid of named zones
  - SpatialExtent[BoundingBox] for actor footprints inside zones
  - SpatialMap for point/bbox queries against actor positions
  - derive_space_relations to auto-build the adjacency graph from geometry

Each tick, actors probabilistically move to an adjacent zone.  Adjacency
is derived purely from geometry — no hand-coded graph needed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ometeotl_core.model.space_relations import SpaceRelationGraph
from ometeotl_core.model.spaces import Space

from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.coordinate_system import CARTESIAN_2D
from ometeotl_foundations.spatial.coordinates import Coordinate2D
from ometeotl_foundations.spatial.geometric_space import GeometricSpace
from ometeotl_foundations.spatial.relation_derivation import derive_space_relations
from ometeotl_foundations.spatial.spatial_extent import SpatialExtent
from ometeotl_foundations.spatial.spatial_map import SpatialMap

from .config import SimConfig

# Palette for actors (cycles if num_actors > len)
_ACTOR_COLORS = [
    "#e63946",
    "#457b9d",
    "#2a9d8f",
    "#f4a261",
    "#8338ec",
    "#ffbe0b",
    "#06d6a0",
    "#fb5607",
    "#3a86ff",
    "#ff006e",
    "#8ecae6",
    "#95d5b2",
    "#cdb4db",
    "#ffc8dd",
    "#bde0fe",
    "#caffbf",
]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class Actor:
    """Runtime state for one actor."""

    actor_id: str
    zone_id: str
    color: str
    # Position within the zone in world coordinates (centre of a 1-unit footprint)
    pos_x: float
    pos_y: float


@dataclass
class SimState:
    """Full mutable runtime state of the simulation."""

    config: SimConfig
    # zone_id → GeometricSpace[BoundingBox]
    zones: Dict[str, GeometricSpace[BoundingBox]]
    # Derived adjacency / containment graph
    relation_graph: SpaceRelationGraph
    # actor_id → SpatialExtent[BoundingBox] (1-unit footprint at actor position)
    spatial_map: SpatialMap[BoundingBox]
    # actor_id → Actor
    actors: Dict[str, Actor]
    # Ordered zone list for display
    zone_order: List[str]
    tick: int = 0
    event_log: List[str] = field(default_factory=list)
    _rng: random.Random = field(default_factory=random.Random, repr=False)


# ---------------------------------------------------------------------------
# Grid construction
# ---------------------------------------------------------------------------


def _zone_id(row: int, col: int) -> str:
    return f"zone-r{row}-c{col}"


def _build_zones(config: SimConfig) -> Dict[str, GeometricSpace[BoundingBox]]:
    """Create a grid of GeometricSpace[BoundingBox] zones."""
    zones: Dict[str, GeometricSpace[BoundingBox]] = {}
    step = config.zone_size + config.zone_gap
    for row in range(config.grid_rows):
        for col in range(config.grid_cols):
            min_x = col * step
            min_y = row * step
            max_x = min_x + config.zone_size
            max_y = min_y + config.zone_size
            zid = _zone_id(row, col)
            space = Space(id=zid)
            space.label = f"R{row}C{col}"
            geom = BoundingBox(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)
            zones[zid] = GeometricSpace(
                space=space,
                geometry=geom,
                coordinate_system=CARTESIAN_2D,
                metadata={"row": row, "col": col},
            )
    return zones


# ---------------------------------------------------------------------------
# Actor helpers
# ---------------------------------------------------------------------------


def _actor_start_pos(
    zone: GeometricSpace[BoundingBox], jitter_x: float, jitter_y: float
) -> Tuple[float, float]:
    """Return a world position within the zone, offset by jitter in [0,1]."""
    geom: BoundingBox = zone.geometry  # type: ignore[assignment]
    margin = geom.max_x - geom.min_x  # == zone_size
    x = geom.min_x + margin * (0.2 + jitter_x * 0.6)
    y = geom.min_y + margin * (0.2 + jitter_y * 0.6)
    return x, y


def _make_extent(actor: Actor) -> SpatialExtent[BoundingBox]:
    """Build a 1-unit BoundingBox footprint at the actor's current position."""
    return SpatialExtent(
        space_id=actor.zone_id,
        geometry=BoundingBox(
            min_x=actor.pos_x - 0.5,
            min_y=actor.pos_y - 0.5,
            max_x=actor.pos_x + 0.5,
            max_y=actor.pos_y + 0.5,
        ),
        coordinate_system=CARTESIAN_2D,
    )


# ---------------------------------------------------------------------------
# create_sim
# ---------------------------------------------------------------------------


def create_sim(config: SimConfig) -> SimState:
    """Build a fresh SimState from *config*."""
    config.validate()
    rng = random.Random(config.seed)

    zones = _build_zones(config)
    zone_order = sorted(zones.keys())

    # Derive adjacency graph purely from geometry.
    # adjacency_tolerance is set slightly above zone_gap so touching (gap=0)
    # and near-touching zones both register as adjacent_to.
    adjacency_tolerance = config.zone_gap + 0.001
    relation_graph = derive_space_relations(
        zones.values(),
        adjacency_tolerance=adjacency_tolerance,
        derive_containment=False,  # uniform grid — no containment
        derive_intersection=False,
        derive_adjacency=True,
    )

    # Place actors randomly across zones
    zone_ids = list(zone_order)
    spatial_map: SpatialMap[BoundingBox] = SpatialMap()
    actors: Dict[str, Actor] = {}

    for i in range(config.num_actors):
        actor_id = f"actor-{i}"
        zone_id = rng.choice(zone_ids)
        zone = zones[zone_id]
        jx = rng.random()
        jy = rng.random()
        px, py = _actor_start_pos(zone, jx, jy)
        color = _ACTOR_COLORS[i % len(_ACTOR_COLORS)]
        actor = Actor(
            actor_id=actor_id, zone_id=zone_id, color=color, pos_x=px, pos_y=py
        )
        actors[actor_id] = actor
        spatial_map.set_extent(actor_id, _make_extent(actor))

    state = SimState(
        config=config,
        zones=zones,
        relation_graph=relation_graph,
        spatial_map=spatial_map,
        actors=actors,
        zone_order=zone_order,
    )
    state._rng = random.Random(rng.randint(0, 2**32 - 1))

    state.event_log.append(
        f"[tick 0] Simulation started. "
        f"{config.grid_cols}×{config.grid_rows} grid "
        f"({len(zones)} zones), {config.num_actors} actors, "
        f"gap={config.zone_gap}."
    )
    return state


# ---------------------------------------------------------------------------
# step
# ---------------------------------------------------------------------------


def step(state: SimState) -> None:
    """Advance the simulation by one tick.

    Each actor independently decides whether to move (probability =
    config.move_probability). If moving, it picks a random adjacent zone
    from the derived relation graph and relocates.
    """
    moves = 0
    for actor in state.actors.values():
        if state._rng.random() > state.config.move_probability:
            continue

        neighbors = state.relation_graph.neighbors_of(actor.zone_id)
        if not neighbors:
            continue

        target_zone_id = state._rng.choice(neighbors)
        old_zone_id = actor.zone_id

        # Relocate actor within the new zone
        jx = state._rng.random()
        jy = state._rng.random()
        new_zone = state.zones[target_zone_id]
        px, py = _actor_start_pos(new_zone, jx, jy)

        actor.zone_id = target_zone_id
        actor.pos_x = px
        actor.pos_y = py

        # Update SpatialMap
        state.spatial_map.set_extent(actor.actor_id, _make_extent(actor))

        state.event_log.append(
            f"[tick {state.tick + 1}] {actor.actor_id} moved "
            f"{old_zone_id} → {target_zone_id}"
        )
        moves += 1

    if moves == 0:
        state.event_log.append(f"[tick {state.tick + 1}] No actors moved this tick.")

    state.tick += 1


# ---------------------------------------------------------------------------
# serialize_state
# ---------------------------------------------------------------------------


def _world_bounds(config: SimConfig) -> Tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) of the entire grid in world units."""
    step = config.zone_size + config.zone_gap
    total_w = (
        config.grid_cols * config.zone_size + (config.grid_cols - 1) * config.zone_gap
    )
    total_h = (
        config.grid_rows * config.zone_size + (config.grid_rows - 1) * config.zone_gap
    )
    return 0.0, 0.0, total_w, total_h


def serialize_state(state: SimState) -> dict:
    """Return a JSON-compatible dict for the web UI."""
    config = state.config
    min_wx, min_wy, max_wx, max_wy = _world_bounds(config)
    world_w = max(max_wx - min_wx, 1.0)
    world_h = max(max_wy - min_wy, 1.0)

    # Actor count per zone for heatmap
    actor_count_by_zone: Dict[str, int] = {zid: 0 for zid in state.zone_order}
    actors_by_zone: Dict[str, List[str]] = {zid: [] for zid in state.zone_order}
    for actor in state.actors.values():
        actor_count_by_zone[actor.zone_id] = (
            actor_count_by_zone.get(actor.zone_id, 0) + 1
        )
        actors_by_zone.setdefault(actor.zone_id, []).append(actor.actor_id)

    # Adjacency edges (deduplicated)
    seen_edges: set = set()
    adjacency_edges = []
    for zid in state.zone_order:
        for nb in state.relation_graph.neighbors_of(zid):
            key = (min(zid, nb), max(zid, nb))
            if key not in seen_edges:
                seen_edges.add(key)
                # Centroid positions (normalized 0-1 for SVG)
                ga: BoundingBox = state.zones[zid].geometry  # type: ignore[assignment]
                gb: BoundingBox = state.zones[nb].geometry  # type: ignore[assignment]
                adjacency_edges.append(
                    {
                        "a": zid,
                        "b": nb,
                        "ax": (ga.centroid.x - min_wx) / world_w,
                        "ay": (ga.centroid.y - min_wy) / world_h,
                        "bx": (gb.centroid.x - min_wx) / world_w,
                        "by": (gb.centroid.y - min_wy) / world_h,
                    }
                )

    # Zones
    zones_out = []
    for zid in state.zone_order:
        gs = state.zones[zid]
        geom: BoundingBox = gs.geometry  # type: ignore[assignment]
        zones_out.append(
            {
                "zone_id": zid,
                "row": gs.metadata.get("row", 0),
                "col": gs.metadata.get("col", 0),
                "label": gs.space.label or zid,
                # Normalised [0,1] coords for SVG rendering
                "x": (geom.min_x - min_wx) / world_w,
                "y": (geom.min_y - min_wy) / world_h,
                "w": (geom.max_x - geom.min_x) / world_w,
                "h": (geom.max_y - geom.min_y) / world_h,
                "area": geom.area,
                "centroid_x": (geom.centroid.x - min_wx) / world_w,
                "centroid_y": (geom.centroid.y - min_wy) / world_h,
                "actor_count": actor_count_by_zone.get(zid, 0),
                "actors": sorted(actors_by_zone.get(zid, [])),
                "neighbor_count": len(state.relation_graph.neighbors_of(zid)),
            }
        )

    # Actors
    actors_out = [
        {
            "actor_id": a.actor_id,
            "zone_id": a.zone_id,
            "color": a.color,
            "x": (a.pos_x - min_wx) / world_w,
            "y": (a.pos_y - min_wy) / world_h,
        }
        for a in state.actors.values()
    ]

    # Spatial query stats — exercise SpatialMap at serialize time
    world_centre = Coordinate2D(
        x=(min_wx + max_wx) / 2.0,
        y=(min_wy + max_wy) / 2.0,
    )
    actors_near_centre = state.spatial_map.ids_containing_point(world_centre)

    return {
        "tick": state.tick,
        "zones": zones_out,
        "actors": actors_out,
        "adjacency_edges": adjacency_edges,
        "event_log": state.event_log[-30:],
        "config": config.to_dict(),
        "stats": {
            "zone_count": len(state.zones),
            "actor_count": len(state.actors),
            "adjacency_edge_count": len(adjacency_edges),
            "actors_near_world_centre": actors_near_centre,
        },
    }
