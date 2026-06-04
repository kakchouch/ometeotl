# Lab 12: Devastation

Lab 12 extends [Lab 11](../lab11_technology/) with a **per-node devastation system**.
Nodes that change faction ownership accumulate devastation, which degrades their
economic output and makes them less attractive conquest targets.

## Devastation Mechanics

### Accumulation and Recovery

Each owned node carries a `devastation` score in `[0.0, 1.0]`.

| Event | Effect |
|-------|--------|
| Node flipped (ownership change) | `devastation += flip_increment` (clamped to 1.0) |
| Node stable for one tick | `devastation -= recovery_rate` (floored at 0.0) |
| Node neutral (no owner) | Devastation unchanged |

Flip events are recorded in a rolling history window (`devastation_window_size` ticks).
The audit field `flip_count_in_window` reports how many flips occurred within that window.

### Economic Effects (multiplicative)

**Stock cap** — the logi-scaled cap is further reduced by devastation:

```
effective_cap = max(min_stock_cap, logi_cap × (1 − devastation × cap_penalty))
```

**Base production** — a per-tick bonus on top of `spice_flow` is degraded:

```
effective_production = spice_flow + max(min_node_production,
                           base_node_production × (1 − devastation × production_penalty))
```

`spice_flow` (the node's intrinsic richness) is never degraded by devastation.

### Planner Integration (perception-aware)

The conquest attractiveness formula uses **perceived** devastation, not ground truth:

```
offense_score = (perceived_production / distance) × relation_factor
              × max(0, 1 − perceived_devastation × attractiveness_penalty)
```

- In **limited** perception mode: devastation of unperceived nodes is unknown → neutral modifier `1.0`.
- In **full** perception mode: ground truth devastation is always used.

The planner never reads `node.devastation` directly — only `_get_perceived_devastation`.

## UI Features

- **Devastation ring**: rose-red arc around each node proportional to its devastation score.
- **Node info popup**: shows `Devastation %`, `Eff. cap`, `Eff. prod`, `Flips (win)`.
- **Config panel**: Devastation section with all 9 parameters.
- **Auto-untangle**: force-directed layout with edge-crossing resolution (⚡ button).

## Core Files

- `config.py` — Lab 11 parameters + 9 devastation parameters.
- `engine.py` — Full simulation engine with devastation layer.
- `graph_gen.py` — Graph generation (independent copy, no lab11 dependency).
- `perception.py` — Fog-of-war perception layer (independent copy).
- `web_server.py` — HTTP API server on port `8775`.
- `web/` — UI with devastation ring visualisation and devastation config fields.
- `test_sim_local.py` — 22 tests covering all 10 spec invariants.

## New Configuration Parameters

```python
from examples.lab12_devastation.config import SimConfig

cfg = SimConfig(
    # ... all Lab 11 params ...

    # Devastation
    devastation_window_size=10,         # rolling flip history window (ticks)
    devastation_flip_increment=0.3,     # devastation added per flip
    devastation_recovery_rate=0.01,     # devastation removed per stable tick
    devastation_cap_penalty=0.5,        # fraction of logi_cap lost at full devastation
    devastation_production_penalty=0.5, # fraction of base_node_production lost at full devastation
    devastation_attractiveness_penalty=0.7,  # offense score penalty at full devastation
    base_node_production=2.0,           # global per-tick production bonus (degradable)
    min_stock_cap=1.0,                  # floor for effective stock cap
    min_node_production=0.0,            # floor for effective base production
)
```

## Running Lab 12

```bash
cd /path/to/ometeotl
python -m examples.lab12_devastation.web_server
```

Server URL: `http://127.0.0.1:8775/`

## Running Tests

```bash
python -m pytest examples/lab12_devastation/test_sim_local.py -v
```
