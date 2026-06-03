---
title: "Examples"
description: "Runnable simulation examples demonstrating Ometeotl core concepts"
---

This section documents the runnable examples in [examples/](https://github.com/kakchouch/ometeotl/tree/main/examples/).

Each example is a self-contained simulation that exercises one or more ometeotl_core layers (perception, projection, strategy, teleology). All examples ship with a web UI server and a local test suite.

---

## Lab series

The lab series builds incrementally. Each lab extends the previous one with one new layer.

### [Lab 2 — Multi-agent graph conquest](https://github.com/kakchouch/ometeotl/tree/main/examples/multi_agent_sim/)

Baseline multi-agent simulation. Factions compete for node ownership on a random graph. Full omniscience (no fog of war). Web UI on port `8766`.

### [Lab 3 — Limited perception](https://github.com/kakchouch/ometeotl/tree/main/examples/lab3_perception_sim/)

Extends Lab 2 with **fog-of-war** via the ometeotl_core `Sensor` + `CoverageRule` stack. Factions can only perceive owned spaces and immediate neighbors. `perception_mode` toggle between `"limited"` and `"full"`. Web UI on port `8767`.

### [Lab 4 — Logistics](https://github.com/kakchouch/ometeotl/tree/main/examples/lab4_logistics_sim/)

Extends Lab 3 by moving resource ownership from factions to nodes. Spice moves along capacity-constrained links. Conquest is achieved by physically routing spice toward enemy territory. Web UI on port `8768`.

### [Lab 5 — Behavior matrix](https://github.com/kakchouch/ometeotl/tree/main/examples/lab5_behavior_sim/)

Extends Lab 4 with a per-faction `BehaviorProfile` matrix with four independent axes in `[0, 1]`: engagement threshold (E), concentration (C), liquidity preference (L), and objective bias (O). The planner uses these to filter targets, spread or focus force, and modulate spend. Web UI on port `8769`.

### [Lab 6 — Vassal relations](https://github.com/kakchouch/ometeotl/tree/main/examples/lab6_vassal_sim/)

Extends Lab 5 by adding a fifth behavior axis — centralization (Z) — and a vassal hierarchy where subordinate factions route a share of their income upward. Web UI on port `8770`.

### [Lab 7 — Centralization dynamics](https://github.com/kakchouch/ometeotl/tree/main/examples/lab7_centralization_sim/)

Extends Lab 6 with emergent centralization: factions can dynamically shift their Z axis based on territory share and pressure, creating feedback between administrative cost and expansion drive. Web UI on port `8771`.

### [Lab 8 — Inter-faction relations](https://github.com/kakchouch/ometeotl/tree/main/examples/lab8_relations_sim/)

Extends Lab 7 with pairwise symmetric relation scores in `[0, 1]`. Pressure lowers relation; passive growth recovers it. Relation modulates offense appetite (high relation → lower aggression toward that faction). Web UI on port `8772`.

### [Lab 9 — Globalization](https://github.com/kakchouch/ometeotl/tree/main/examples/lab9_globalization_sim/)

Extends Lab 8 with network globalization dynamics. The initial topology may be disconnected. Each tick, a rare endogenous event either strengthens an existing link or bridges disconnected components. Web UI on port `8773`.

### [Lab 10 — Complex behavior with symbolic AI](https://github.com/kakchouch/ometeotl/tree/main/examples/lab10_complex_behavior_sim/)

Extends Lab 9 with teleological faction reasoning. Each tick, every active faction synthesizes a core-model [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) and [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/) from context signals (frontier pressure, territory share, relation climate, disconnected-node ratio). The resulting symbolic mode deterministically shifts the behavior axes before the normal planner runs. Web UI on port `8774`.

---

## Strategy game demo

### [Strategy game](https://github.com/kakchouch/ometeotl/tree/main/examples/strategy_game/)

A minimal local-only two-player strategy game with a shared deterministic engine, CLI mode, and a browser UI with SVG board. Demonstrates end-to-end use of the ometeotl_core strategy + projection layers in an interactive setting.

```bash
# CLI
python -m examples.strategy_game.cli

# Web UI (http://127.0.0.1:8765)
python -m examples.strategy_game.web_server
```

---

## Running any lab

From the repository root:

```bash
python -m examples.<lab_folder>.web_server
```

Then open the URL shown in the terminal (each lab uses a distinct port).

To run a lab's local test suite:

```bash
python -m pytest examples/<lab_folder>/test_sim_local.py -v
```
