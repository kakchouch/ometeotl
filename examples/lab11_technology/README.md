# Lab 11: Technology

Lab 11 extends [Lab 10](../lab10_complex_behavior_sim/) with a **technology investment
pipeline**.  Each faction accumulates three independent tech levels via a 7-step stochastic
process that runs every tick after economic planning.

## Technology Axes

| Axis | Symbol | Effect |
|------|--------|--------|
| **Diplomacy** | Diplo | Inflates the attacker's perceived relation with the Diplo holder, reducing enemy aggression. Creates asymmetry: high-Diplo factions can be aggressive while suffering less retaliation. |
| **Cohesion** | Cohé | Raises the Hamming secession threshold — territory becomes culturally more stable and harder to fracture. |
| **Logistics** | Logi | Reduces the proportional transport gas fee (`transport_gas_fee`) for this faction's shipments. |

All three axes start at `0.0` and increase monotonically — there is no decay.

## Investment Pipeline (v0 → v6)

| Step | Name | Description |
|------|------|-------------|
| v0 | Die roll | Random unit vector in the positive octant, seeded by `config.seed` via `state._rng`. |
| v1 | E-inertia | Blends v0 with the rolling history mean. High `E` (engagement threshold) → more conservative / inertial. |
| v2 | C-burst/cooldown | `C` (concentration) amplifies v1 when recent magnitude is low (burst), then zeroes it when high (cooldown). `burst_threshold = 0.3 + C × 0.4`. |
| v3 | O-direction deform | Hadamard product of the α signal vector and an `O`-weighted directional bias shifts the investment direction. |
| v4 | Z-smoothing | Exponential blend with the previous pending vector; weight controlled by `Z` (centralization). |
| v5 | Rubberbanding | Per-axis: global leader pays `1 + tech_leader_cost_multiplier`; follower behind a border neighbor gains `max(0.1, 1 − tech_neighbor_acceleration × gap)` acceleration. |
| v6 | Economic truncation | Scales magnitude down if total cost > available spice reserves. Direction is strictly preserved. |

## Signal Extraction and α-Vector

Per tick, signals are derived from the faction's perception and combined into an α vector
(investment directional bias):

| Signal | Axes driven |
|--------|-------------|
| Frontier pressure | Diplo, Logi |
| Mean relation inverse | Diplo |
| Min relation inverse | Diplo |
| Owned-fraction inverse | Diplo, Cohé, Logi |
| Disconnected-node ratio | Cohé |
| Known-ratio inverse | Logi, Diplo |

## Pipeline Invariants

1. **ECLOZ is immutable** — the pipeline never writes behavior axes (`E/C/L/O/Z`), genome, or relation graph.
2. **Strictly unidirectional** — no step reads the output of a later step.
3. **History lag** — the rolling history window is updated at tick start; it never contains the current tick's output.
4. **Direction preservation** — the economic truncation step (v6) only scales magnitude.
5. **Monotone growth** — tech levels never decrease.

## Tech Effects Integration

Effects are committed at the **start of tick T+1** (one-tick delay), after the pipeline runs
at the end of tick T:

- **Diplo**: applied in `_relation_pressure_factor` — `rel_perceived = clamp(rel + diplo × diplo_effect)`
- **Cohé**: applied in `_mutate_and_check_secession` — `threshold += round(cohe × genome_length × cohe_bonus)`
- **Logi**: applied in `_execute_transport` — `fee = max(0, gas_fee × (1 − logi × logi_reduction))`

## Serialised Audit Fields

Every tick the API adds three audit fields per faction:

```json
"tech":            { "diplo": 0.012, "cohe": 0.008, "logi": 0.015 },
"tech_investment": { "diplo": 0.003, "cohe": 0.002, "logi": 0.004 },
"tech_alpha":      { "diplo": 0.61,  "cohe": 0.28,  "logi": 0.72  }
```

## Core Files

- `config.py` — 18 new technology parameters (α weights, rubberbanding, costs, effects).
- `engine.py` — 7-step pipeline, signal extraction, rubberbanding, effect application.
- `web_server.py` — HTTP API server on port `8774`.
- `web/` — UI with per-faction technology panel (levels, investment, α bias).
- `test_sim_local.py` — 5 invariant tests + 3 effect tests + seed / config tests.

## New Configuration Parameters

```python
from examples.lab11_technology.config import SimConfig

cfg = SimConfig(
    # ... all Lab 10 params ...

    # Technology — α signal weights
    tech_alpha_weight_pressure_diplo=0.4,
    tech_alpha_weight_pressure_logi=0.3,
    tech_alpha_weight_relation_inv_diplo=0.3,
    tech_alpha_weight_min_relation_inv_diplo=0.5,
    tech_alpha_weight_owned_fraction_inv_diplo=0.2,
    tech_alpha_weight_owned_fraction_cohe=0.3,
    tech_alpha_weight_owned_fraction_logi=0.3,
    tech_alpha_weight_disconnected_cohe=0.8,
    tech_alpha_weight_known_ratio_inv_logi=0.3,
    tech_alpha_weight_known_ratio_inv_diplo=0.2,

    # Technology — rubberbanding
    tech_leader_cost_multiplier=1.5,
    tech_neighbor_acceleration=0.3,

    # Technology — economy
    tech_rnd_base_cost=10.0,
    tech_rnd_history_window=5,
    tech_reserve_reference=50.0,

    # Technology — effect strengths
    tech_diplo_perception_effect=0.3,
    tech_cohe_threshold_bonus=0.3,
    tech_logi_cost_reduction=0.5,
)
```

## Running Lab 11

```bash
cd /path/to/ometeotl
python -m examples.lab11_technology.web_server
```

Server URL: `http://127.0.0.1:8774/`

## Running Tests

```bash
python -m pytest examples/lab11_technology/test_sim_local.py -v
```
