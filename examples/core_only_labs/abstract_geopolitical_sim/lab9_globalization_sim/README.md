# Lab 9: Globalization Simulation

Lab 9 extends [Lab 8](../lab8_relations_sim/) with network globalization dynamics.

In addition to Lab 8 relations and behavior layers, Lab 9 introduces:

- geographic generation where disconnected regions are allowed at start,
- rare endogenous network evolution at each tick:
    - either one existing link gains `+1` capacity,
    - or one new `1.0` capacity bridge appears between disconnected components.

Relations are still active:

- known faction pairs track a symmetric relation score in `[0, 1]`,
- pressure lowers relation,
- passive growth recovers relation,
- relation modulates offense appetite.

## Globalization Rules

- Initial topology may be disconnected when `allow_disconnected_regions=1`.
- Per tick, at most one globalization event is applied.
- Capacity growth chance: `globalization_link_growth_chance`.
- Bridge spawn chance: `globalization_bridge_spawn_chance`.
- New globalization bridges always start at capacity `1.0`.

## Core Files

- `config.py`: logistics + behavior + relation + globalization config.
- `graph_gen.py`: supports disconnected regional generation.
- `engine.py`: relation dynamics + globalization tick events.
- `web_server.py`: HTTP API server on port `8773`.
- `web/`: UI controls including globalization knobs.
- `test_sim_local.py`: local tests for relations and globalization events.

## Configuration

```python
from examples.lab9_globalization_sim.config import SimConfig

cfg = SimConfig(
        num_nodes=14,
        num_factions=3,
        perception_mode="limited",

        # Logistics
        initial_node_spice=5.0,
        min_link_flow=3.0,
        max_link_flow=12.0,
        max_spice_move_fraction=0.7,
        transport_base_cost=1.0,
        transport_gas_fee=0.05,
        centralization_admin_cost=1.0,

        # Behavior (includes Z centralization)
        behavior_engagement_min=0.2,
        behavior_engagement_max=0.8,
        behavior_concentration_min=0.2,
        behavior_concentration_max=0.8,
        behavior_liquidity_min=0.2,
        behavior_liquidity_max=0.8,
        behavior_objective_min=0.2,
        behavior_objective_max=0.8,
        behavior_centralization_min=0.2,
        behavior_centralization_max=0.8,

        # Relations
        relation_initial=0.85,
        relation_growth_rate=0.01,
        relation_pressure_impact=0.015,
        relation_offense_bias=0.6,

        # Globalization
        allow_disconnected_regions=1,
        globalization_link_growth_chance=0.01,
        globalization_bridge_spawn_chance=0.005,
)
```

## Running Lab 9

```bash
cd /path/to/ometeotl
python -m examples.lab9_globalization_sim.web_server
```

Server URL: `http://127.0.0.1:8773/`

## Running Tests

```bash
python -m pytest examples/lab9_globalization_sim/test_sim_local.py -v
```
