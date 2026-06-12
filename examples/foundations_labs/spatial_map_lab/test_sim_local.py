"""Tests for the Spatial Map Lab.

These tests live under examples/ and are NOT part of the tracked tests/ tree.
Run with:
    python -m pytest -q examples/foundations_labs/spatial_map_lab/test_sim_local.py

What is exercised:
  - BoundingBox geometry (area, centroid, contains, intersects, distance)
  - GeometricSpace construction and serialisation round-trip
  - SpatialExtent serialisation round-trip
  - CoordinateSystem singletons and round-trip
  - derive_space_relations adjacency derivation from geometry
  - SpatialMap.ids_containing_point and ids_intersecting
  - Actor placement, movement, and SpatialMap update
  - serialize_state correctness
"""

from __future__ import annotations

import pytest

from ometeotl_foundations.spatial.bounding_box import BoundingBox
from ometeotl_foundations.spatial.coordinate_system import (
    CARTESIAN_2D,
    CARTESIAN_3D,
    GRID,
    WGS84,
    CoordinateKind,
    CoordinateSystem,
)
from ometeotl_foundations.spatial.coordinates import (
    Coordinate2D,
    GeoCoordinate,
    GridCell,
)
from ometeotl_foundations.spatial.geometry import Geometry
from ometeotl_foundations.spatial.spatial_extent import SpatialExtent

from examples.foundations_labs.spatial_map_lab.config import SimConfig
from examples.foundations_labs.spatial_map_lab.engine import (
    SimState,
    create_sim,
    serialize_state,
    step,
    _build_zones,
    _make_extent,
    _zone_id,
)

# ---------------------------------------------------------------------------
# SimConfig validation
# ---------------------------------------------------------------------------


def test_config_defaults_valid():
    SimConfig().validate()


def test_config_rejects_single_column():
    with pytest.raises(ValueError):
        SimConfig(grid_cols=1).validate()


def test_config_rejects_negative_gap():
    with pytest.raises(ValueError):
        SimConfig(zone_gap=-1.0).validate()


def test_config_rejects_zero_zone_size():
    with pytest.raises(ValueError):
        SimConfig(zone_size=0.0).validate()


def test_config_rejects_invalid_move_probability():
    with pytest.raises(ValueError):
        SimConfig(move_probability=1.5).validate()
    with pytest.raises(ValueError):
        SimConfig(move_probability=-0.1).validate()


def test_config_to_dict_round_trip():
    cfg = SimConfig(
        grid_cols=3, grid_rows=3, zone_size=50.0, zone_gap=8.0, num_actors=5
    )
    d = cfg.to_dict()
    cfg2 = SimConfig.from_dict(d)
    assert cfg2.grid_cols == 3
    assert cfg2.zone_size == 50.0
    assert cfg2.zone_gap == 8.0


# ---------------------------------------------------------------------------
# BoundingBox geometry
# ---------------------------------------------------------------------------


def test_bounding_box_area():
    bb = BoundingBox(0, 0, 10, 5)
    assert bb.area == pytest.approx(50.0)


def test_bounding_box_centroid():
    bb = BoundingBox(0, 0, 100, 100)
    assert bb.centroid == Coordinate2D(50.0, 50.0)


def test_bounding_box_contains_self():
    bb = BoundingBox(0, 0, 10, 10)
    assert bb.contains(bb)


def test_bounding_box_contains_inner():
    outer = BoundingBox(0, 0, 100, 100)
    inner = BoundingBox(10, 10, 90, 90)
    assert outer.contains(inner)
    assert not inner.contains(outer)


def test_bounding_box_intersects_overlap():
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(5, 5, 15, 15)
    assert a.intersects(b)
    assert b.intersects(a)


def test_bounding_box_no_intersect_disjoint():
    a = BoundingBox(0, 0, 5, 5)
    b = BoundingBox(10, 10, 20, 20)
    assert not a.intersects(b)


def test_bounding_box_touches_shared_edge():
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(10, 0, 20, 10)
    assert a.touches(b)
    assert b.touches(a)


def test_bounding_box_distance_zero_when_overlapping():
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(5, 5, 15, 15)
    assert a.distance(b) == pytest.approx(0.0)


def test_bounding_box_distance_gap():
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(20, 0, 30, 10)
    assert a.distance(b) == pytest.approx(10.0)


def test_bounding_box_from_center():
    centre = Coordinate2D(5.0, 5.0)
    bb = BoundingBox.from_center(centre, half_w=2.0, half_h=3.0)
    assert bb.min_x == pytest.approx(3.0)
    assert bb.max_y == pytest.approx(8.0)


def test_bounding_box_from_point_degenerate():
    pt = Coordinate2D(7.0, 3.0)
    bb = BoundingBox.from_point(pt)
    assert bb.area == pytest.approx(0.0)
    assert bb.centroid == pt


def test_bounding_box_satisfies_geometry_protocol():
    bb = BoundingBox(0, 0, 1, 1)
    assert isinstance(bb, Geometry)


def test_bounding_box_to_dict_round_trip():
    bb = BoundingBox(1.5, 2.5, 3.5, 4.5)
    d = bb.to_dict()
    bb2 = BoundingBox.from_dict(d)
    assert bb2 == bb


def test_bounding_box_from_dict_wrong_type():
    with pytest.raises(ValueError):
        BoundingBox.from_dict(
            {"type": "point", "min_x": 0, "min_y": 0, "max_x": 1, "max_y": 1}
        )


def test_bounding_box_expand():
    bb = BoundingBox(10, 10, 20, 20)
    expanded = bb.expand(5)
    assert expanded.min_x == pytest.approx(5.0)
    assert expanded.max_x == pytest.approx(25.0)


def test_bounding_box_union():
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(5, 5, 20, 20)
    u = a.union(b)
    assert u.min_x == pytest.approx(0.0)
    assert u.max_x == pytest.approx(20.0)


def test_bounding_box_contains_point():
    bb = BoundingBox(0, 0, 10, 10)
    assert bb.contains_point(Coordinate2D(5, 5))
    assert bb.contains_point(Coordinate2D(0, 0))  # boundary
    assert not bb.contains_point(Coordinate2D(11, 5))


# ---------------------------------------------------------------------------
# CoordinateSystem
# ---------------------------------------------------------------------------


def test_coordinate_system_singletons_valid():
    assert CARTESIAN_2D.kind == CoordinateKind.CARTESIAN
    assert WGS84.srid == 4326
    assert GRID.kind == CoordinateKind.GRID
    assert CARTESIAN_3D.kind == CoordinateKind.CARTESIAN


def test_coordinate_system_to_dict_round_trip():
    for cs in (CARTESIAN_2D, CARTESIAN_3D, WGS84, GRID):
        d = cs.to_dict()
        cs2 = CoordinateSystem.from_dict(d)
        assert cs2 == cs


def test_coordinate_system_from_dict_missing_key():
    with pytest.raises(ValueError):
        CoordinateSystem.from_dict({"name": "x", "unit": "m"})  # missing 'kind'


def test_coordinate_system_from_dict_bad_kind():
    with pytest.raises(ValueError):
        CoordinateSystem.from_dict({"name": "x", "kind": "unknown", "unit": "m"})


# ---------------------------------------------------------------------------
# GeoCoordinate and GridCell
# ---------------------------------------------------------------------------


def test_geo_coordinate_valid():
    gc = GeoCoordinate(longitude=2.35, latitude=48.85)
    assert gc.longitude == pytest.approx(2.35)


def test_geo_coordinate_rejects_invalid_longitude():
    with pytest.raises(ValueError):
        GeoCoordinate(longitude=200.0, latitude=0.0)


def test_geo_coordinate_rejects_invalid_latitude():
    with pytest.raises(ValueError):
        GeoCoordinate(longitude=0.0, latitude=91.0)


def test_grid_cell_negative_coords_valid():
    gc = GridCell(col=-3, row=-5, layer=0)
    assert gc.col == -3


# ---------------------------------------------------------------------------
# GeometricSpace (via _build_zones)
# ---------------------------------------------------------------------------


def test_build_zones_count():
    cfg = SimConfig(grid_cols=3, grid_rows=2)
    zones = _build_zones(cfg)
    assert len(zones) == 6


def test_build_zones_correct_area():
    cfg = SimConfig(grid_cols=2, grid_rows=2, zone_size=50.0)
    zones = _build_zones(cfg)
    for gs in zones.values():
        geom: BoundingBox = gs.geometry  # type: ignore[assignment]
        assert geom.area == pytest.approx(50.0 * 50.0)


def test_build_zones_coordinate_system():
    cfg = SimConfig(grid_cols=2, grid_rows=2)
    zones = _build_zones(cfg)
    for gs in zones.values():
        assert gs.coordinate_system == CARTESIAN_2D


def test_build_zones_metadata_row_col():
    cfg = SimConfig(grid_cols=3, grid_rows=2)
    zones = _build_zones(cfg)
    gs = zones[_zone_id(1, 2)]
    assert gs.metadata["row"] == 1
    assert gs.metadata["col"] == 2


def test_geometric_space_to_dict_round_trip():
    cfg = SimConfig(grid_cols=2, grid_rows=2)
    zones = _build_zones(cfg)
    for gs in zones.values():
        d = gs.to_dict()
        from ometeotl_foundations.spatial.geometric_space import GeometricSpace

        gs2 = GeometricSpace.from_dict(d, BoundingBox.from_dict)
        assert gs2.id == gs.id
        assert gs2.geometry == gs.geometry
        assert gs2.coordinate_system == gs.coordinate_system


# ---------------------------------------------------------------------------
# SpatialExtent
# ---------------------------------------------------------------------------


def test_spatial_extent_to_dict_round_trip():
    ext = SpatialExtent(
        space_id="zone-r0-c0",
        geometry=BoundingBox(10, 10, 20, 20),
        coordinate_system=CARTESIAN_2D,
        metadata={"note": "test"},
    )
    d = ext.to_dict()
    ext2 = SpatialExtent.from_dict(d, BoundingBox.from_dict)
    assert ext2.space_id == ext.space_id
    assert ext2.geometry == ext.geometry
    assert ext2.metadata == ext.metadata


# ---------------------------------------------------------------------------
# derive_space_relations — adjacency via geometry
# ---------------------------------------------------------------------------


def test_adjacent_zones_touching_gap_zero():
    """With gap=0 zones share a boundary; they must be adjacent_to each other."""
    cfg = SimConfig(grid_cols=2, grid_rows=2, zone_size=100.0, zone_gap=0.0)
    state = create_sim(cfg)
    left = _zone_id(0, 0)
    right = _zone_id(0, 1)
    neighbors = state.relation_graph.neighbors_of(left)
    assert right in neighbors


def test_adjacent_zones_with_gap():
    """With a positive gap, adjacency_tolerance covers it and zones are still adjacent."""
    cfg = SimConfig(grid_cols=2, grid_rows=2, zone_size=100.0, zone_gap=10.0)
    state = create_sim(cfg)
    left = _zone_id(0, 0)
    right = _zone_id(0, 1)
    assert right in state.relation_graph.neighbors_of(left)


def test_non_adjacent_zones_not_neighbors():
    """Zones separated by more than adjacency_tolerance must not be neighbors."""
    # With gap=10, adjacency_tolerance=10.001 covers immediate neighbors but not
    # zones two steps apart (distance = 2*(zone_size+gap) >> tolerance).
    cfg = SimConfig(grid_cols=4, grid_rows=2, zone_size=100.0, zone_gap=10.0)
    state = create_sim(cfg)
    # zone-r0-c0 and zone-r0-c3 are separated by 330 world units — not adjacent
    far_left = _zone_id(0, 0)
    far_right = _zone_id(0, 3)
    assert far_right not in state.relation_graph.neighbors_of(far_left)


def test_corner_zone_has_three_neighbors_with_gap_zero():
    """With gap=0, corner-touching zones also count as adjacent (8-connectivity).
    Top-left corner in a 3×3 grid therefore has 3 neighbours: right, below, diagonal."""
    cfg = SimConfig(grid_cols=3, grid_rows=3, zone_size=100.0, zone_gap=0.0)
    state = create_sim(cfg)
    tl = _zone_id(0, 0)
    assert len(state.relation_graph.neighbors_of(tl)) == 3


def test_interior_zone_has_eight_neighbors_with_gap_zero():
    """With gap=0 an interior zone has 8 neighbours (4-connected + 4 diagonals)."""
    cfg = SimConfig(grid_cols=4, grid_rows=4, zone_size=100.0, zone_gap=0.0)
    state = create_sim(cfg)
    centre = _zone_id(1, 1)
    assert len(state.relation_graph.neighbors_of(centre)) == 8


# ---------------------------------------------------------------------------
# SpatialMap queries
# ---------------------------------------------------------------------------


def test_spatial_map_has_entry_for_each_actor():
    cfg = SimConfig(grid_cols=3, grid_rows=3, num_actors=6, seed=1)
    state = create_sim(cfg)
    assert len(state.spatial_map.all_ids()) == 6


def test_spatial_map_ids_containing_point_inside_zone():
    """An actor's SpatialExtent centroid should be found by ids_containing_point
    when the point lands inside the extent."""
    cfg = SimConfig(
        grid_cols=2, grid_rows=2, num_actors=1, seed=7, move_probability=0.0
    )
    state = create_sim(cfg)
    actor = list(state.actors.values())[0]
    # The actor extent is a 1x1 box centred at (actor.pos_x, actor.pos_y)
    hit = state.spatial_map.ids_containing_point(Coordinate2D(actor.pos_x, actor.pos_y))
    assert actor.actor_id in hit


def test_spatial_map_ids_intersecting_zone_bbox():
    """Querying with a zone's full BoundingBox should return all actors in that zone."""
    cfg = SimConfig(grid_cols=3, grid_rows=3, num_actors=10, seed=5)
    state = create_sim(cfg)
    # Find a zone that has at least one actor
    occupied = None
    for actor in state.actors.values():
        if occupied is None or actor.zone_id == occupied:
            occupied = actor.zone_id
    assert occupied is not None
    zone_geom: BoundingBox = state.zones[occupied].geometry  # type: ignore[assignment]
    found = state.spatial_map.ids_intersecting(zone_geom)
    # All actors in the occupied zone must appear in the result
    actors_in_zone = [
        a.actor_id for a in state.actors.values() if a.zone_id == occupied
    ]
    for aid in actors_in_zone:
        assert aid in found


# ---------------------------------------------------------------------------
# Simulation step
# ---------------------------------------------------------------------------


def test_step_increments_tick():
    cfg = SimConfig(seed=1)
    state = create_sim(cfg)
    step(state)
    assert state.tick == 1


def test_step_actors_stay_in_valid_zones():
    cfg = SimConfig(grid_cols=4, grid_rows=4, num_actors=8, seed=3)
    state = create_sim(cfg)
    for _ in range(10):
        step(state)
    for actor in state.actors.values():
        assert actor.zone_id in state.zones


def test_step_updates_spatial_map():
    """After each step the SpatialMap entry should reflect the actor's new position."""
    cfg = SimConfig(
        grid_cols=3, grid_rows=3, num_actors=4, seed=2, move_probability=1.0
    )
    state = create_sim(cfg)
    before = {aid: state.spatial_map.get_extent(aid) for aid in state.actors}
    step(state)
    for actor in state.actors.values():
        extent = state.spatial_map.get_extent(actor.actor_id)
        assert extent is not None
        assert extent.space_id == actor.zone_id


def test_step_with_zero_move_probability_no_movement():
    """With move_probability=0 no actor should move."""
    cfg = SimConfig(
        grid_cols=3, grid_rows=3, num_actors=6, seed=8, move_probability=0.0
    )
    state = create_sim(cfg)
    zones_before = {aid: a.zone_id for aid, a in state.actors.items()}
    step(state)
    for aid, a in state.actors.items():
        assert a.zone_id == zones_before[aid]


def test_multi_step_no_error():
    cfg = SimConfig(grid_cols=5, grid_rows=4, num_actors=15, seed=42)
    state = create_sim(cfg)
    for _ in range(50):
        step(state)
    assert state.tick == 50


# ---------------------------------------------------------------------------
# serialize_state
# ---------------------------------------------------------------------------


def test_serialize_zone_count():
    cfg = SimConfig(grid_cols=3, grid_rows=2)
    state = create_sim(cfg)
    d = serialize_state(state)
    assert len(d["zones"]) == 6


def test_serialize_actor_count():
    cfg = SimConfig(num_actors=7, seed=1)
    state = create_sim(cfg)
    d = serialize_state(state)
    assert len(d["actors"]) == 7


def test_serialize_adjacency_edges_non_empty():
    cfg = SimConfig(grid_cols=3, grid_rows=3)
    state = create_sim(cfg)
    d = serialize_state(state)
    assert len(d["adjacency_edges"]) > 0


def test_serialize_zones_have_required_keys():
    cfg = SimConfig(grid_cols=2, grid_rows=2)
    state = create_sim(cfg)
    d = serialize_state(state)
    for z in d["zones"]:
        for key in ("zone_id", "x", "y", "w", "h", "area", "actor_count", "actors"):
            assert key in z, f"Missing key '{key}' in zone dict"


def test_serialize_actors_have_required_keys():
    cfg = SimConfig(num_actors=3, seed=1)
    state = create_sim(cfg)
    d = serialize_state(state)
    for a in d["actors"]:
        for key in ("actor_id", "zone_id", "color", "x", "y"):
            assert key in a, f"Missing key '{key}' in actor dict"


def test_serialize_normalized_coords_in_range():
    """All zone and actor normalised coords must be in [0, 1]."""
    cfg = SimConfig(grid_cols=4, grid_rows=3, num_actors=10, seed=1)
    state = create_sim(cfg)
    d = serialize_state(state)
    for z in d["zones"]:
        assert 0.0 <= z["x"] <= 1.0
        assert 0.0 <= z["y"] <= 1.0
        assert z["w"] > 0
        assert z["h"] > 0
    for a in d["actors"]:
        assert 0.0 <= a["x"] <= 1.0
        assert 0.0 <= a["y"] <= 1.0


def test_serialize_event_log_non_empty():
    cfg = SimConfig(seed=1)
    state = create_sim(cfg)
    d = serialize_state(state)
    assert len(d["event_log"]) >= 1


def test_serialize_stats_fields():
    cfg = SimConfig(grid_cols=3, grid_rows=3, num_actors=5, seed=1)
    state = create_sim(cfg)
    d = serialize_state(state)
    stats = d["stats"]
    assert stats["zone_count"] == 9
    assert stats["actor_count"] == 5
    assert "adjacency_edge_count" in stats
    assert "actors_near_world_centre" in stats
