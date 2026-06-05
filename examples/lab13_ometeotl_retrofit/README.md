# Lab 13: Ometeotl Retro-Fit

Lab 13 is a fork of [Lab 12](../lab12_devastation/) focused on **Ometeotl-first modeling**.
It keeps the Lab 12 devastation gameplay mechanics while refactoring runtime entities so
the simulation is driven by Ometeotl objects and relations.

## Ometeotl-First Runtime Model

Lab 13 runtime now follows these principles:

- **Faction is an Actor (inheritance)**: each faction is represented by a `Faction` class
    inheriting from `ometeotl_core.model.actors.Actor`.
- **Node is an Actor (inheritance)**: each node is represented by a `Node` class inheriting
    from `ometeotl_core.model.actors.Actor`.
- **Spice is a Resource**: each node stock is represented by a `Resource` object,
    synchronized with simulation stock updates.
- **Ownership as composition + resource relations**:
    - owning faction actor has the node actor as a `component`
    - owning faction actor links to node spice resource through `resource`
    - spice resource links back to owner actor through `owner`/`user`
- **Actions as Action objects**: key faction operations (production, transfer, pressure,
    admin transfer, conquest, secession, centralization spending) are recorded as
    `ometeotl_core.model.actions.Action` objects.

## Secession Semantics

On secession, Lab 13 models actor decomposition explicitly:

1. Remove previous faction composition/resource links for the node.
2. Create and register a new faction actor.
3. Re-attach node actor and node spice resource to the new faction actor.

This implements the intended composition break and independent actor emergence.

## Devastation Mechanics (Inherited from Lab 12)

Each owned node carries a devastation score in `[0.0, 1.0]`.

| Event | Effect |
|-------|--------|
| Node flipped | `devastation += flip_increment` (clamped to 1.0) |
| Stable owned tick | `devastation -= recovery_rate` (floored at 0.0) |
| Neutral node | unchanged |

Economic effects remain identical to Lab 12:

- `effective_cap = max(min_stock_cap, logi_cap * (1 - devastation * cap_penalty))`
- `effective_production = spice_flow + max(min_node_production, base_node_production * (1 - devastation * production_penalty))`

Planner integration remains perception-aware:

- Offense attractiveness uses **perceived devastation** in limited perception mode.
- Unknown devastation remains neutral in scoring.

## Core Files

- `config.py`: simulation parameters (including devastation controls)
- `engine.py`: inheritance-based Ometeotl retrofit + simulation loop
- `graph_gen.py`: topology generation
- `perception.py`: fog-of-war perception layer
- `web_server.py`: API server (port `8776`)
- `web/`: browser UI
- `test_sim_local.py`: local invariant tests

## Run Lab 13

```bash
cd /path/to/ometeotl
python -m examples.lab13_ometeotl_retrofit.web_server
```

Server URL: `http://127.0.0.1:8776/`

## Run Tests

```bash
python -m pytest examples/lab13_ometeotl_retrofit/test_sim_local.py -v
```
