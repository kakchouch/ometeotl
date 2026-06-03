# Lab 4: Logistics Multi-Agent Simulation

A logistics-based variant of the multi-agent graph conquest simulation, extending [Lab 3](../lab3_perception_sim/) with **spice transport mechanics**: spice now lives in nodes (not factions), moves along capacity-constrained links, and conquest is achieved by physically routing spice toward enemy territory.

## Overview

Lab 4 keeps the fog-of-war perception from Lab 3 and adds a full logistics layer:

- **Spice is node-resident**: Each node holds a `spice_stock`. Factions have no stock of their own.
- **Transport bottlenecks**: Every graph link has a `max_flow` capacity. A link can only carry so much spice per tick.
- **Gas fees**: Each shipment burns a **flat base cost** (overhead per move) plus a **proportional fee** (fraction of moved amount). This rewards coordinated, focused, bulk movement and punishes scattered micro-shipments.
- **Logistics conquest**: Factions conquer nodes by routing spice into enemy/neutral nodes as pressure. There is no abstract "spend from stock" — spice must physically travel there.
- **Spice seizure**: When a node flips, its unallocated `spice_stock` is seized and deposited into the conqueror's capital node.
- **Fog-of-war**: Inherited from Lab 3. In `limited` mode, factions only see their territory and immediate neighbors.

## Key Differences from Lab 3

| Feature | Lab 3 | Lab 4 |
|---------|-------|-------|
| **Spice location** | Faction stock | Node stock (`Node.spice_stock`) |
| **Conquest mechanism** | Allocate faction budget proportionally | Route spice physically via links |
| **Link properties** | Adjacency only | Adjacency + `max_flow` capacity |
| **Gas fee** | None | Flat base cost + proportional fee per hop |
| **Spice seizure** | No | Yes — flipped node stock goes to conqueror |
| **Web port** | 8767 | 8768 |

## Gas Fee Mechanics

Two fees apply to every shipment, compounding to discourage scatter:

### Flat base cost (`transport_base_cost`)

A fixed amount of spice burned from the source node **per order**, regardless of shipment size.

| Strategy | Orders | Base cost paid | Total overhead |
|----------|--------|---------------|----------------|
| 10 × 1-unit scattered moves | 10 | `10 × base_cost` | High |
| 1 × 10-unit focused move | 1 | `1 × base_cost` | Low |

A move order is rejected entirely if `node.spice_stock ≤ base_cost` (net-negative shipments are blocked).

### Proportional fee (`transport_gas_fee`)

A fraction of the moved amount is destroyed in transit:

```
delivered = amount × (1 - transport_gas_fee)
```

Multi-hop routes compound this fee at every link.

### Combined effect

```
source loses:   base_cost + amount
target receives: amount × (1 - gas_fee)   [if friendly]
target gains pressure: amount × (1 - gas_fee)   [if enemy/neutral]
```

## Architecture

### Core Modules

- **[config.py](config.py)**: All tunable parameters including the two gas fee fields.
- **[engine.py](engine.py)**: Logistics engine — node stocks, link capacity, transport execution, conquest via pressure, seizure on flip.
- **[perception.py](perception.py)**: Fog-of-war layer (unchanged from Lab 3).
- **[graph_gen.py](graph_gen.py)**: Graph generation (uniform random + geographic).
- **[web_server.py](web_server.py)**: HTTP API server (port 8768).
- **[web/](web/)**: HTML/CSS/JS UI.

### Data Model

#### `Node`
```python
Node(
    node_id: str,
    spice_flow: int,       # per-tick income added to this node's stock
    spice_stock: float,    # spice physically located here
    owner_id: str | None,
    genome: list[int],
    pressure: dict[str, float],        # per-attacker pressure this tick
    pressure_accumulated: float,       # cumulative conquest pressure
)
```

#### `Link`
```python
Link(
    source_id: str,
    target_id: str,
    max_flow: float,   # maximum spice per tick across this link
    used_flow: float,  # committed this tick (reset each tick)
)
```

#### `Faction`
```python
Faction(
    faction_id: str,
    capital_id: str,
    genome: list[int],
    color: str,
    move_orders: list[tuple[str, str, float]],  # (src, dst, amount) per tick
)
```
Note: `spice_stock` has been removed from `Faction`. Spice lives in `Node`.

### Tick Order

```
1. Reset link usage counters
2. Collect income → each owned node gains node.spice_flow
3. Plan AI move orders (perception-aware in limited mode)
4. Execute transport:
     for each order (src, dst, amount):
       - burn base_cost from src
       - burn amount from src
       - deliver amount × (1 - gas_fee) to dst
         → if dst is friendly: add to dst.spice_stock
         → if dst is enemy/neutral: add to dst.pressure_accumulated
5. Apply conquest: nodes with pressure_accumulated ≥ flip_threshold flip
     → flipped node: spice_stock seized → deposited at conqueror's capital
6. Genome mutation + secession check
7. Victory check
8. tick += 1
```

## Configuration

Key fields (all in [config.py](config.py)):

```python
from examples.lab4_logistics_sim.config import SimConfig

cfg = SimConfig(
    num_nodes=14,
    num_factions=3,
    seed=42,
    initial_node_spice=5.0,       # starting stock on each node
    min_link_flow=3.0,            # minimum link transport capacity
    max_link_flow=12.0,           # maximum link transport capacity
    max_spice_move_fraction=0.7,  # max fraction of node stock dispatchable per tick
    transport_base_cost=1.0,      # flat overhead burned per shipment (punishes scatter)
    transport_gas_fee=0.05,       # proportional fraction lost per hop
    flip_threshold=20.0,          # pressure needed to conquer a node
    perception_mode="limited",    # "limited" (fog-of-war) or "full" (omniscient)
)
```

## Running Lab 4

```bash
cd /path/to/ometeotl
python -m examples.lab4_logistics_sim.web_server
```

Server runs at: `http://127.0.0.1:8768/`

## Running Tests

```bash
python -m pytest examples/lab4_logistics_sim/test_sim_local.py -v
```

26 tests covering: config validation, gas fee economics (scatter vs bulk), link capacity enforcement, income into nodes, pressure from transport, seizure on conquest, serialization, and integration steps.


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
