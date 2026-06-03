# Lab 5: Behavior Matrix Logistics Simulation

Lab 5 extends [Lab 4](../lab4_logistics_sim/) by adding a faction behavior matrix.

Each faction still plays on the same logistics model (node-resident spice, link flow limits, base transport fee, proportional gas fee), but now uses a distinct strategic profile to decide:

- when to engage,
- whether to focus or spread,
- how much to spend now vs keep in reserve,
- whether to prioritize offense or defense.

## Behavior Matrix Axes

Each faction has a `BehaviorProfile` with 4 independent axes in `[0, 1]`:

- `engagement_threshold` (E): minimum normalized offensive attractiveness needed to engage.
  - High E: opportunistic, attacks only when the target is clearly strong.
  - Low E: aggressive, attacks even mediocre targets.

- `concentration` (C): force focus vs spread.
  - High C: concentrates on few top targets.
  - Low C: spreads pressure across more targets.

- `liquidity_preference` (L): reserve preference.
  - High L: conserves spice, lower dispatch rate.
  - Low L: spends aggressively each tick.

- `objective_bias` (O): offense vs defense weighting.
  - High O: offense/territorial pressure.
  - Low O: defense/economic stabilization.

## Planner Integration

In `engine.py`, `_plan_moves()` uses the matrix in this order:

1. Build offense and defense scores.
2. Apply engagement filtering on offense with E.
3. Mix offense and defense with O.
4. Keep top-K targets where K depends on C.
5. Dispatch with spend fraction reduced by L.

The transport and conquest pipeline remains Lab 4 compatible:

- base fee + gas fee at transport,
- pressure from delivered hostile shipments,
- seizure of unallocated node stock on flip.

## Core Files

- `config.py`: logistics + behavior-range config.
- `engine.py`: behavior-aware planning and serialization.
- `web_server.py`: HTTP API server on port `8769`.
- `web/`: UI and controls for behavior ranges.
- `test_sim_local.py`: local tests including behavior assertions.

## Configuration

```python
from examples.lab5_behavior_sim.config import SimConfig

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

    # Behavior axis ranges sampled independently per faction
    behavior_engagement_min=0.2,
    behavior_engagement_max=0.8,
    behavior_concentration_min=0.2,
    behavior_concentration_max=0.8,
    behavior_liquidity_min=0.2,
    behavior_liquidity_max=0.8,
    behavior_objective_min=0.2,
    behavior_objective_max=0.8,
)
```

## Running Lab 5

```bash
cd /path/to/ometeotl
python -m examples.lab5_behavior_sim.web_server
```

Server URL: `http://127.0.0.1:8769/`

## Running Tests

```bash
python -m pytest examples/lab5_behavior_sim/test_sim_local.py -v
```
