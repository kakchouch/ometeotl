# Lab 3: Limited Perception Multi-Agent Simulation

A perception-based variant of the multi-agent graph conquest simulation, introducing **fog-of-war** mechanics where factions can only see their owned territories and immediate neighbors.

## Overview

Lab 3 extends [Lab 2](../multi_agent_sim/) with **limited perception**. Instead of omniscient AI, factions operate under fog-of-war:

- **Owned spaces**: The faction can see all spaces it owns.
- **Neighbors**: The faction can see spaces adjacent to its owned territories.
- **Beyond neighbors**: Distant spaces are invisible; the faction cannot target them for conquest.

This creates asymmetric information and more realistic strategic constraints.

## Key Differences from Lab 2

| Feature | Lab 2 | Lab 3 |
|---------|-------|-------|
| **Perception** | Full omniscience | Limited (owned + neighbors) |
| **Config** | No perception setting | `perception_mode: "limited"` or `"full"` |
| **AI targeting** | All unowned neighbors visible | Only visible borders targetable |
| **Web port** | 8766 | 8767 |

## Architecture

### Core Modules

- **[config.py](config.py)**: Simulation configuration with `perception_mode` field.
- **[perception.py](perception.py)**: Ometeotl perception layer (fog-of-war via `FactionCoverageRule`).
- **[engine.py](engine.py)**: Simulation engine with perception-aware priority assignment.
- **[graph_gen.py](graph_gen.py)**: Graph generation (uniform random + geographic map-like).
- **[web_server.py](web_server.py)**: HTTP API server for web UI.
- **[web/](web/)**: HTML/CSS/JS UI for real-time simulation viewing.

### Perception Mechanics

**File**: [perception.py](perception.py)

#### `FactionCoverageRule`
A custom Ometeotl `CoverageRule` that limits what a faction can perceive:

- **`evaluate_space(space, world)`**: Returns `True` if space is owned or a neighbor of owned space.
- **`evaluate_membership(membership, world)`**: Filters to only visible spaces.
- **`evaluate_relation(relation, world)`**: Only includes relations between visible spaces.
- **`evaluate_component_link(link, world)`**: Filters composite links to visible components.

#### `get_faction_perception(state, faction_id)`
Builds a `Perception` object for a faction:

1. Collects owned space IDs.
2. Collects neighboring space IDs via `relation_graph.neighbors_of()`.
3. Creates `FactionCoverageRule` with visible space set.
4. Calls `sensor.sense(world, relation_graph)` to build perception.
5. Returns `Perception` object.

#### `visible_border_targets(perception, owned_set)`
Extracts conquest targets from a perception object:

- Iterates `perception.perceived_relations`.
- Returns sorted list of unowned neighbors visible from owned spaces.

### Engine Integration

**File**: [engine.py](engine.py)

The simulation engine integrates perception into priority assignment:

```python
def step(state):
    ...
    for faction in factions:
        if state.config.perception_mode == "limited":
            perception = get_faction_perception(state, faction.faction_id)
        else:
            perception = None

        _assign_priorities(state, faction, perception)
    ...
```

In `_assign_priorities()`:
- If `perception` is provided: calls `visible_border_targets(perception, owned)`.
- If `perception` is `None`: calls `state.border_targets_for()` (full omniscience).

## Configuration

### `perception_mode` Field

```python
from examples.lab3_perception_sim.config import SimConfig

# Limited perception (fog-of-war)
cfg_limited = SimConfig(perception_mode="limited")

# Full omniscience (Lab 2-like)
cfg_full = SimConfig(perception_mode="full")
```

**Valid values**: `"limited"`, `"full"` (default: `"limited"`)

All other configuration fields (num_nodes, num_factions, seed, etc.) work identically to Lab 2.

## Running Lab 3

### Start the Server

```bash
cd /path/to/ometeotl
python -m examples.lab3_perception_sim.web_server
```

Server runs at: `http://127.0.0.1:8767/`

### Web UI

Open the browser to `http://127.0.0.1:8767/` and interact with:

- **Map**: SVG visualization of node ownership and conquest pressure.
- **Faction legend**: Current faction stats (nodes, spice stock, income, genome).
- **Configuration panel**: Adjust simulation parameters including **Perception mode** dropdown.
- **Controls**: Step, auto-run, reset.

### Perception Mode Dropdown

In the configuration form, select:

- **Limited (neighbors only)**: Factions can only target visible borders.
- **Full omniscience**: Factions see the entire world (Lab 2 behavior).

Changes take effect on **Apply & Reset**.

## Testing

### Run All Tests

```bash
python -m pytest -q examples/lab3_perception_sim/test_sim_local.py
```

### Key Test Cases

**Perception-specific tests**:

1. **`test_perception_includes_owned_and_neighbors`**: Verifies perception = owned ∪ neighbors.
2. **`test_perception_excludes_distant_nodes`**: Ensures distance-2+ nodes are invisible.
3. **`test_limited_ai_only_targets_visible`**: Confirms limited AI only targets visible borders.
4. **`test_full_mode_identical_to_omniscience`**: Validates full mode matches Lab 2.
5. **`test_step_with_limited_perception`**: Smoke test for simulation loop with limited perception.

**Inherited from Lab 2**:

- Config validation
- Graph generation
- Genome utilities (Hamming distance, mutation)
- Simulation initialization
- Step mechanics
- Conquest and secession

## Expected Behavior

### Limited Perception (`perception_mode="limited"`)

- Factions only see owned + neighbor spaces.
- AI assigns priorities only to visible border targets.
- If a faction has no visible targets, it waits (no conquest actions).
- Fog-of-war creates strategic asymmetry: factions cannot plan attacks on distant enemies.

### Full Omniscience (`perception_mode="full"`)

- All factions see the entire world graph.
- AI assigns priorities to all unowned neighbors.
- Identical to Lab 2 behavior (useful for regression testing).

## Files

```
examples/lab3_perception_sim/
├── __init__.py              # Package marker
├── config.py                # SimConfig with perception_mode field
├── perception.py            # Fog-of-war via Ometeotl Sensor + CoverageRule
├── engine.py                # Simulation engine with perception integration
├── graph_gen.py             # Graph generation (from Lab 2)
├── web_server.py            # HTTP API server (port 8767)
├── test_sim_local.py        # Perception + inherited test suite
├── web/
│   ├── index.html           # UI with perception_mode dropdown
│   ├── app.js               # Client logic with perception mode support
│   └── styles.css           # Dark theme styling
└── README.md                # This file
```

## Notes

- **Duplication**: Lab 3 is a standalone copy of Lab 2 logic. If shared engine improvements are needed, both labs will need updating.
- **Perception recomputation**: Perception is recalculated every tick (not cached) to simplify state management.
- **Optional perception parameter**: The engine's `_assign_priorities()` function accepts an optional `perception` parameter, maintaining backward compatibility.

## References

- **Ometeotl ontology**: [ometeotl_core/model/](../../src/ometeotl_core/model/)
- **Perception module**: [ometeotl_core/perception/](../../src/ometeotl_core/)
- **Lab 2 (omniscience baseline)**: [../multi_agent_sim/](../multi_agent_sim/)
