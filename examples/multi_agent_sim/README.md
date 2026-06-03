# Multi-Agent Graph Simulation (Lab 2)

This lab is a local, git-ignored simulation that demonstrates faction competition on an undirected graph with resource-driven conquest, genome drift, and faction secession.

## Goals

- Simulate a non-oriented graph world where each node has a random spice flow.
- Start with N factions, each owning one capital node.
- Let factions accumulate spice stock from controlled nodes.
- Conquer neighboring nodes through weighted resource pressure.
- Model genome drift as random point mutations weighted by distance to capital.
- Spawn new factions when node drift from parent faction exceeds threshold.
- Provide full-map visibility and full parameter control through a web UI.

## Location and Scope

- Main package: examples/multi_agent_sim
- Runtime server: examples/multi_agent_sim/web_server.py
- Engine: examples/multi_agent_sim/engine.py
- Graph generator: examples/multi_agent_sim/graph_gen.py
- Config model: examples/multi_agent_sim/config.py
- Web UI: examples/multi_agent_sim/web/
- Smoke tests: examples/multi_agent_sim/test_sim_local.py

This lab is intentionally outside tracked source modules and exists for experimentation.

## Quick Start

1. Activate your virtual environment.
2. Start the web server:

```bash
python -m examples.multi_agent_sim.web_server
```

3. Open:

http://127.0.0.1:8766

4. Use:
- Step for single-tick progression
- Auto-run to advance continuously
- Apply & Reset to restart with custom parameters

## Simulation Mechanics

### Graph and Nodes

- Graph is undirected and connected.
- A spanning tree is built first, then extra edges are added from graph density.
- Each node receives:
  - spice flow (RNG in [min_spice_flow, max_spice_flow])
  - owner (faction or neutral)
  - local genome bitfield
  - UI position (ring or grid layout)

### Factions

Each faction has:
- faction id
- capital node id
- faction genome bitfield
- spice stock
- per-tick target priorities

Initial state:
- N factions are created.
- Each faction gets one capital node.
- Capital node genome matches faction genome.

### Economy

At each tick, each faction gains income equal to total spice flow of nodes it controls.

### Symbolic AI Priorities

For each faction, border targets are scored with full information:

score = spice_flow / bfs_distance_from_capital

Scores are normalized into weights that sum to 1.0.

### Conquest

- A faction spends its spice stock across border targets using normalized weights.
- Spent amount contributes pressure on target nodes.
- A node flips when cumulative pressure reaches flip_threshold.
- The highest-pressure attacker becomes new owner.
- On flip, node genome is replaced by conqueror faction genome.

### Genome Drift and Secession

- Controlled node genomes can mutate by point mutation each tick.
- Mutation probability is increased with distance from faction capital.
- Hamming distance between node genome and faction genome is measured.
- If distance >= drift_threshold_bits, the node secedes and creates a new faction.

New faction behavior:
- starts immediately
- inherits the node genome
- uses seceding node as capital
- participates from next simulation progression like any other faction

### End Conditions

- Full domination: one faction controls all nodes.
- Max ticks: if max_ticks > 0, winner is faction with most nodes when limit is reached.

## Configuration Parameters

All parameters are available from the UI and API.

| Parameter | Type | Default | Meaning |
|---|---:|---:|---|
| num_nodes | int | 14 | Number of graph nodes |
| num_factions | int | 3 | Starting factions |
| seed | int or null | 42 | RNG seed |
| min_spice_flow | int | 1 | Node spice lower bound |
| max_spice_flow | int | 8 | Node spice upper bound |
| graph_density | float | 0.25 | Extra edge density factor |
| flip_threshold | float | 20.0 | Pressure required to flip node |
| drift_threshold_fraction | float | 0.5 | Drift threshold as genome fraction |
| genome_length | int | 16 | Bitfield length |
| mutation_rate | float | 0.05 | Base mutation probability |
| max_ticks | int | 0 | Stop tick (0 = unlimited) |
| layout | string | ring | UI layout (ring or grid) |
| graph_mode | string | uniform | Graph generation style (uniform or geographic) |

Derived value:

- drift_threshold_bits = round(drift_threshold_fraction * genome_length), min 1

## HTTP API

### GET /api/state

Returns full current simulation state:
- tick, game_over, winner_id
- factions map
- nodes list
- edges list
- recent event log
- active config

### POST /api/step

Advances one tick and returns updated state.

### POST /api/reset

Reinitializes simulation.

Body:
- optional full or partial config payload
- if omitted, defaults are used

### POST /api/config

Merges provided config fields with current config, then reinitializes simulation.

### POST /api/autorun

Body example:

```json
{
  "running": true,
  "interval_ms": 500
}
```

Starts or stops server-side auto progression.

## Test Command

Run local smoke tests:

```bash
python -m pytest -q examples/multi_agent_sim/test_sim_local.py
```

Current expected status in this environment:
- Passed: 18
- Skipped: 2

The two skipped tests are guarded for degenerate small-map initial states where faction-0 only owns its capital and no extra owned node is available for forced secession setup.

## Notes

- This lab intentionally uses examples only.
- No hidden information is used by AI.
- The UI always shows the full graph.
- Node values are RNG-generated each reset.
- Geographic mode creates clustered areas, sparse bridges, and dead ends to resemble map-like terrain structure.
