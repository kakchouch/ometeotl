# Lab 7: Centralization Simulation

Lab 7 extends [Lab 5](../lab5_behavior_sim/) by adding a centralization trait `Z`.

The simulation still uses the Lab 5 logistics model:

- node-resident spice,
- link flow limits,
- base transport cost,
- proportional gas fee.

Centralization adds a second use of the transport layer:

- factions can dispatch admin spice to their own nodes,
- that spice must travel through the same link-capacity and gas-fee pipeline,
- the delivered admin spice is then spent to reduce genetic drift on the target node.

## Z Trait

Each faction has a `BehaviorProfile` with 5 independent axes in `[0, 1]`:

- `engagement_threshold` (E): offense gate.
- `concentration` (C): focus vs spread.
- `liquidity_preference` (L): reserve vs spend.
- `objective_bias` (O): offense vs defense.
- `centralization` (Z): how strongly the faction spends admin spice to suppress drift.

Z interpretation:

- `Z = 1.0`: the faction aggressively resists drift.
- `Z = 0.0`: the faction does not combat drift.

## Core Files

- `config.py`: logistics + behavior-range config.
- `engine.py`: behavior-aware planning, admin transport, and serialization.
- `web_server.py`: HTTP API server on port `8771`.
- `web/`: UI and controls for the Z range.
- `test_sim_local.py`: local tests including centralization assertions.

## Configuration

```python
from examples.lab7_centralization_sim.config import SimConfig

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

    # Behavior axis ranges sampled independently per faction
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
)
```

## Running Lab 7

```bash
cd /path/to/ometeotl
python -m examples.lab7_centralization_sim.web_server
```

Server URL: `http://127.0.0.1:8771/`

## Running Tests

```bash
python -m pytest examples/lab7_centralization_sim/test_sim_local.py -v
```
