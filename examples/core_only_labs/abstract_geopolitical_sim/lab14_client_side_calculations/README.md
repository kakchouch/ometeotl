# Lab 14: Client-Side Calculations

Lab 14 is a fork of [Lab 13](../lab13_ometeotl_retrofit/) focused on **client-side calculations**.
It keeps the Lab 13 Ometeotl-first runtime model while moving simulation logic from the server
to the browser, reducing round-trips and enabling richer client interactivity.

## Goal

Move the heavy lifting of perception, planning, and scoring out of the Python server and into
JavaScript running in the browser. The server becomes a thin state store; the client drives the
simulation tick logic.

## Inherited from Lab 13

- Ometeotl-first runtime model (factions and nodes as Actors, spice as Resource, actions as Action objects)
- Devastation mechanics
- Fog-of-war perception layer
- Graph topology generation

## Core Files

- `config.py`: simulation parameters
- `engine.py`: Ometeotl runtime + simulation loop
- `graph_gen.py`: topology generation
- `perception.py`: fog-of-war perception layer
- `web_server.py`: API server (port `8777`)
- `web/`: browser UI (target for client-side logic)
- `test_sim_local.py`: local invariant tests

## Run Lab 14

```bash
cd /path/to/ometeotl
python -m examples.lab14_client_side_calculations.web_server
```

Server URL: `http://127.0.0.1:8777/`

## Run Tests

```bash
python -m pytest examples/lab14_client_side_calculations/test_sim_local.py -v
```
