# Lab 8: Relations Simulation

Lab 8 extends [Lab 7](../lab7_centralization_sim/) with inter-faction relations.

Factions that know each other share a symmetric relation metric in `[0, 1]`:

- it starts high when contact is established,
- it grows each tick by a base growth rate,
- it is reduced by pressure spice delivered against the other faction,
- high relation de-incentivizes pressure spending,
- low relation incentivizes pressure spending.

## Relation Rules

- Relation keys are pair-based: `(faction_a, faction_b)`.
- Unknown pairs have no relation value yet.
- Contact events create the relation at `relation_initial`.
- Tick growth applies `relation_growth_rate`, capped at `1.0`.
- Pressure decreases relation by:

    $$\Delta R = -\text{delivered_pressure} \times \text{relation_pressure_impact}$$

- Offense appetite is scaled by relation:

    $$\text{factor} = 1 + b\,(1 - 2R)$$

    where $b = \text{relation_offense_bias}$.

This yields lower offense when relation is high and higher offense when relation is low.

## Core Files

- `config.py`: logistics + behavior + relation config.
- `engine.py`: planning, transport, centralization, relation updates.
- `web_server.py`: HTTP API server on port `8772`.
- `web/`: UI controls for relation parameters.
- `test_sim_local.py`: local tests including relation dynamics.

## Configuration

```python
from examples.lab8_relations_sim.config import SimConfig

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
)
```

## Running Lab 8

```bash
cd /path/to/ometeotl
python -m examples.lab8_relations_sim.web_server
```

Server URL: `http://127.0.0.1:8772/`

## Running Tests

```bash
python -m pytest examples/lab8_relations_sim/test_sim_local.py -v
```
