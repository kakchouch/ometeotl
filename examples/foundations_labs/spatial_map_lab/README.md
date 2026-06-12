# Spatial Map Lab

First lab in the **foundations_labs** series.  Exercises the
`ometeotl_foundations.spatial` layer end-to-end with a running simulation
and a live web UI.

## What it demonstrates

| Concept | Where used |
|---|---|
| `BoundingBox` | Zone extents and actor footprints |
| `Geometry` protocol | All spatial predicates (contains, distance, …) |
| `CoordinateSystem` / `CARTESIAN_2D` | Coordinate frame attached to every zone |
| `GeometricSpace[BoundingBox]` | Each zone in the grid |
| `SpatialExtent[BoundingBox]` | 1-unit actor footprint updated on every move |
| `SpatialMap[BoundingBox]` | Mutable registry of all actor footprints |
| `SpatialMap.ids_containing_point()` | Live point query at the world centre each tick |
| `SpatialMap.all_ids()` | Verified against actor count each tick (stats panel) |
| `derive_space_relations()` | Auto-derives the adjacency graph from zone geometry |
| `SpaceRelationGraph.neighbors_of()` | Actors pick a random adjacent zone to move to |

**Not covered here** (no pure-Python implementation at the foundations layer):
`SpatialIndex` and `SpatialBackend` are adapter-level protocols wired in by
`ometeotl_adapters`; use an adapter lab to exercise those.

## Key behaviour notes

### Adjacency tolerance and 8-connectivity

`derive_space_relations` is called with:

```python
adjacency_tolerance = zone_gap + 0.001
```

When `zone_gap = 0` (touching zones), `BoundingBox.distance()` returns `0.0`
for corner-touching pairs because both dx and dy clamp to 0 at a shared
corner point.  The graph is therefore **8-connected** (diagonals included),
not 4-connected.  Corner zones have 3 neighbors; edge zones 5; interior zones
8.

If you need strictly 4-connected adjacency (no diagonals), you would need a
custom adjacency predicate based on shared-edge length rather than Euclidean
distance.

### SpatialMap entry count invariant

`stats.spatial_map_registered` must always equal `stats.actor_count`.  Both
are shown in the stats panel; a mismatch would indicate a bug in the extent
lifecycle.

## File layout

```
spatial_map_lab/
├── config.py          — SimConfig dataclass (grid, actors, move probability)
├── engine.py          — Zone grid, actor moves, SpatialMap updates, serialisation
├── web_server.py      — ThreadingHTTPServer on port 8790 (GET /api/state, POST /api/step, …)
├── test_sim_local.py  — 58 local tests covering the full spatial layer
└── web/
    ├── index.html     — Two-panel layout (SVG map + event log / stats + config)
    ├── styles.css     — Dark theme
    └── app.js         — SVG rendering: zone heatmap, actor dots, adjacency dashed lines
```

## Running the lab

```bash
cd /path/to/ometeotl
python -m examples.foundations_labs.spatial_map_lab.web_server
```

Open `http://127.0.0.1:8790/` in a browser.

- **Step** — advance one tick manually.
- **Auto-run** — continuous steps at the selected speed.
- **Apply & Reset** — rebuild the simulation from the config form.

## Running tests

```bash
python -m pytest examples/foundations_labs/spatial_map_lab/test_sim_local.py -v
```

58 tests, typically under 0.1 s.

## Configuration

```python
from examples.foundations_labs.spatial_map_lab.config import SimConfig

cfg = SimConfig(
    grid_cols=5,          # columns (2–12)
    grid_rows=4,          # rows (2–12)
    zone_size=100.0,      # world units per zone side
    zone_gap=5.0,         # gap between zones (0 = touching → 8-connected)
    num_actors=12,        # actors placed at tick 0
    seed=42,              # RNG seed (None = random)
    move_probability=0.7, # per-actor per-tick move probability
    max_ticks=0,          # auto-run hard stop (0 = unlimited)
)
```

All fields can also be changed live through the config form in the web UI
without restarting the server.
