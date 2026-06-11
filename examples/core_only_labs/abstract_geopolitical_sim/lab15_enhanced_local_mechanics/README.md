# Lab 15: Enhanced Local Mechanics

Lab 15 is a fork of [Lab 14](../lab14_client_side_calculations/) that introduces three node-level mechanics making local conditions matter more for both conquest stability and genetic divergence.

## New Mechanics

### Pressure Defense
Factions can spend spice to undo incoming pressure on their own nodes. Any spice delivered by a faction to one of its owned nodes that has active pressure is consumed for defense first, at rate `pressure_defense_rate` (1 spice removes that many accumulated pressure points). The remainder goes to stock as normal. The AI already routes spice defensively via its existing `defense_targets` scoring, so the mechanic activates automatically whenever a node is under attack.

### Pressure Decay
Accumulated pressure on a node decays each tick when not continuously applied, at rate `pressure_decay_rate` (fraction removed per tick). Attackers who stop applying spice progressively lose their toehold, making sustained campaigns necessary to flip a node.

### Devastation from Conflict Intensity
Devastation is no longer limited to ownership flips. Every unit of pressure delivered to a node adds `devastation_pressure_rate` devastation (attacker side), and every unit of spice spent on defense adds `devastation_defense_rate` devastation (defender side). A prolonged siege degrades the node regardless of whether it ever changes hands, and successful defense is also costly. Flip-based devastation and passive recovery from Lab 12 remain unchanged.

### Local Mutation Rate
Each node's effective mutation probability is scaled by a local multiplier (≥ 1) that combines four independent signals:
1. **High spice concentration** — stock / effective stock cap
2. **Devastation** — direct use of the devastation score
3. **Pressure** — accumulated pressure normalized by the flip threshold
4. **Neighboring foreign factions** — ratio of distinct non-owner factions among neighbors

Each signal has its own configurable weight (`mutation_spice_weight`, `mutation_devastation_weight`, `mutation_pressure_weight`, `mutation_border_weight`). The result: contested, devastated, overstocked border nodes secede faster, creating natural fragmentation pressure in hot zones.

## Inherited from Lab 14

- Client-side derived calculations (color, effective cap/production, perceived relations)
- Technology pipeline (Diplo / Cohé / Logi)
- Devastation mechanics
- Fog-of-war perception
- Symbolic AI deliberation
- Globalization
- Secession via genome drift

## Core Files

- `config.py`: simulation parameters (6 new Lab 15 params)
- `engine.py`: simulation engine (3 new mechanics)
- `graph_gen.py`: topology generation
- `perception.py`: fog-of-war perception layer
- `web_server.py`: API server (port `8778`)
- `web/`: browser UI
- `test_sim_local.py`: local invariant tests

## Run Lab 15

```bash
cd /path/to/ometeotl
python -m examples.lab15_enhanced_local_mechanics.web_server
```

Server URL: `http://127.0.0.1:8778/`

## Run Tests

```bash
python -m pytest examples/lab15_enhanced_local_mechanics/test_sim_local.py -v
```
