# Lab12 Audit: Ometeotl Usage vs Custom Code Usage

Date: 2026-06-04
Scope: examples/lab12_devastation
Method: static code audit (module inspection + import surface + architecture usage mapping)

## Executive Summary

Lab12 is a hybrid implementation:
- It uses Ometeotl core model types as an integration shell (world graph, actors, perception objects, symbolic goal/strategy objects).
- Most simulation behavior is custom code in the example module (state model, conquest, economy, tech investment, devastation, planning, server/UI).

The current implementation is coherent and test-backed for Lab12 behavior, but there are integration risks where custom runtime state can drift from Ometeotl world state if maintenance paths fail or evolve inconsistently.

## Quantitative Footprint

Total scanned lines in Lab12 modules and UI:
- 5018 lines

Breakdown:
- examples/lab12_devastation/engine.py: 1698
- examples/lab12_devastation/graph_gen.py: 702
- examples/lab12_devastation/perception.py: 142
- examples/lab12_devastation/config.py: 351
- examples/lab12_devastation/web_server.py: 254
- examples/lab12_devastation/test_sim_local.py: 626
- examples/lab12_devastation/web/app.js: 1245

Interpretation:
- Ometeotl usage is strategic and structural.
- Behavioral logic volume is predominantly custom.

## Where Ometeotl Is Used

### 1) Core world and topology objects
Evidence:
- examples/lab12_devastation/engine.py imports and uses World, Space, SpaceRelation, SpaceRelationGraph.
- create_sim builds an Ometeotl world, adds spaces, relations, and actors.

Role:
- Ometeotl is the canonical container for world entities consumed by perception/sensor logic.

### 2) Perception framework
Evidence:
- examples/lab12_devastation/perception.py imports Perception, Sensor, CoverageRule.
- FactionCoverageRule customizes visibility policy, then Sensor.sense builds faction perception from the Ometeotl world.

Role:
- Ometeotl provides the perception data model and sensing mechanism.
- Lab12 customizes only the coverage rule semantics.

### 3) Symbolic layer data types
Evidence:
- examples/lab12_devastation/engine.py imports Goal, Strategy, StrategyNode.
- Symbolic intent creation emits Ometeotl Goal/Strategy objects.

Role:
- Ometeotl provides standardized symbolic/planning object schema.

### 4) Actor registration
Evidence:
- examples/lab12_devastation/engine.py imports Actor during initialization and secession.
- Factions are registered as world objects.

Role:
- Ometeotl object registry is used for identity/object presence in the world model.

## Where Custom Code Dominates

### 1) State and simulation semantics
Evidence:
- Custom dataclasses in engine.py: Node, Link, BehaviorProfile, TechVector, SymbolicIntent, Faction, SimState.
- Tick pipeline and all mechanics are implemented locally: logistics, conquest, mutation/secession, diplomacy dynamics, tech investments, devastation rules.

Impact:
- Behavioral ownership is almost entirely local to Lab12.

### 2) Graph generation and layout
Evidence:
- examples/lab12_devastation/graph_gen.py is a full generator and layout stack.

Impact:
- Topology creation is not delegated to an Ometeotl generator abstraction in this lab.

### 3) HTTP transport and visualization
Evidence:
- examples/lab12_devastation/web_server.py and examples/lab12_devastation/web/app.js are standalone custom server/UI logic.

Impact:
- Presentation and control path are fully custom for the lab environment.

## Findings (ordered by severity)

### High: Dual topology authorities increase drift risk
Evidence:
- Runtime relations are kept in both state.relation_graph and state.world.space_relation_graph (create_sim and _add_runtime_link in engine.py).
- Perception uses Sensor.sense(state.world, faction_id), while many planner/path operations read state.relation_graph.

Risk:
- If any future path updates only one graph, perception and planning can diverge silently (different neighbor sets, inconsistent visible targets).

Recommendation:
- Define one canonical graph authority.
- Either derive one view from the other at read-time, or centralize all topology mutations in one helper that atomically updates both and is the only write path.

### Medium: Silent Actor registration failure on secession
Evidence:
- _secede wraps Actor registration in a broad try/except and ignores errors.

Risk:
- A faction may exist in custom state but be missing from world object registry, reducing observability and potentially impacting subsystems that rely on registered world objects.

Recommendation:
- Replace silent pass with explicit logging into event_log and/or fail-fast in non-demo mode.
- At minimum, record a structured warning for auditability.

### Medium: Heavy local duplication of domain model concepts
Evidence:
- Node/Faction/SimState and rule systems are fully redefined in lab code while also emitting Ometeotl model objects.

Risk:
- Over time, schema and behavior may drift from core conventions, increasing maintenance cost and migration complexity if Lab12 features move toward core modules.

Recommendation:
- Keep this as acceptable for experimental labs, but identify a promotion boundary: which constructs remain example-only versus candidates for model-layer extraction.

### Low: Independent copies pattern acknowledged in docs
Evidence:
- README states graph_gen.py and perception.py are independent copies rather than shared imports from previous labs.

Risk:
- Parallel evolution between labs can diverge and duplicate bug fixes.

Recommendation:
- Consider shared example utilities for common lab infrastructure while preserving lab-specific mechanics.

## Compliance Assessment (with requested lens)

### Ometeotl usage quality
- Good use of Ometeotl model primitives where interoperability matters (world, relations, perception, symbolic objects).
- Integration is real, not superficial.

### Custom code usage quality
- Extensive custom logic is deliberate and consistent with an example/lab context.
- The custom layer is test-covered for Lab12 invariants.
- Main concern is not correctness of custom logic itself, but long-term synchronization boundaries between custom state and Ometeotl world state.

## Suggested Next Actions

1. Introduce a topology sync guard:
- Add one internal assertion/helper to verify equivalence between state.relation_graph and world.space_relation_graph after mutations in debug/test mode.

2. Improve failure transparency in _secede:
- Record Actor registration failures in event_log and include a regression test.

3. Add an architectural note in README:
- Document canonical ownership of graph state and the intended contract between custom simulation state and Ometeotl world objects.

## Conclusion

Lab12 currently uses Ometeotl effectively as a structural substrate and interoperability layer, while intentionally implementing simulation behavior as custom lab code. This split is workable for experimental scenarios, with the primary technical risk centered on keeping dual graph/object representations synchronized as the lab evolves.
