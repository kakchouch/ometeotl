---
title: "Overview"
description: "Three-level walkthrough of how Ometeotl/ometeotl_core works internally"
---

This page explains the internal workings of Ometeotl/ometeotl_core at three depth levels.

For API-level details, use [Class Reference](/ometeotl/documentation/class-reference/).

**04/25/26 - major architectural overhaul:**
  Local tests reveal the current architecture is too abstract for any practical implementation. It has been decided to :
  - to keep the current code in a core module `ometeotl_core`, which is intended to remain abstract;
  - to add a primary layer of specialization `ometeotl_foundations`, including  :
    - spatial: primary layer of spatial implementation of `ometeotl_core`;
    - networks: primary layer of graph theory implementation of `ometeotl_core`
    - ...
  - to add, lastly, an adapter layer `ometeotl_adapters`, which implements each specialization layer with a reputable library.

## Beginner View

Ometeotl/ometeotl_core is a modeling library where everything starts from a generic object, then becomes more specific.

- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/) is the universal base container.
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/) adds practical metadata such as labels, tags, and profiles.
- [Actor](/ometeotl/documentation/class-reference/model/actors/actor/), [Resource](/ometeotl/documentation/class-reference/model/resources/resource/), [Space](/ometeotl/documentation/class-reference/model/spaces/space/), and [Action](/ometeotl/documentation/class-reference/model/actions/action/) represent core domain entities.
- [World](/ometeotl/documentation/class-reference/model/world/world/) is the top-level container that organizes spaces, objects, and their relations.

The library tracks where objects exist with:

- [SpaceObjectMembership](/ometeotl/documentation/class-reference/model/spaces/space-object-membership/)
- [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/)
- [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/)
- [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)

Each actor can have a subjective, possibly imperfect view of the world:

- [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/) builds a [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)
- [CoverageRule](/ometeotl/documentation/class-reference/model/sensor/coverage-rule/) controls what is visible
- [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/) controls how observed data is distorted

Actors may also form explicit composite hierarchies and abstraction layers:

- [Actor](/ometeotl/documentation/class-reference/model/actors/actor/) supports explicit `component` relations for `composite` actors and helper utilities for hierarchy traversal and cycle checks
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/) can be marked `is_abstract` to represent conceptual or analytical spaces alongside canonical spaces
- [Perception](/ometeotl/documentation/class-reference/model/perception/perception/) can carry perceived component links, keeping composition knowledge in the epistemic layer when needed

Candidate actions can then be projected from that perceived state into explicit future-facing strategy artifacts:

- [DefaultProjectionTool](/ometeotl/documentation/class-reference/model/projection/default-projection-tool/) derives projection assumptions and successor perceived states
- [ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/) stores the projected successor perception for one action
- [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/) anchors one action to one input perception and one projected successor perceived state
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/) groups nodes into a linear or branching perception-driven tree

Teleology and utility/ranking are now implemented as model and game extensions:

- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) and [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/) represent final or intermediate objectives and hierarchical decomposition.
- [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/) and [DefaultGoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/default-goal-feasibility-tool/) provide model-level feasibility and admissibility checks.
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/) defines the abstract utility contract.
- [WeightedSumUtility](/ometeotl/documentation/class-reference/game/utility/weighted-sum-utility/), [LexicographicUtility](/ometeotl/documentation/class-reference/game/utility/lexicographic-utility/), and [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/) provide game-layer utility derivation and strategy ranking over projected terminal states.

For server-authoritative setups, mutations can be routed through:

- [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/)
- [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)
- [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
- [AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/)

## Intermediate View

The implemented pipeline follows this flow:

1. Build domain entities from [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)-derived classes such as [Actor](/ometeotl/documentation/class-reference/model/actors/actor/), [Resource](/ometeotl/documentation/class-reference/model/resources/resource/), [Space](/ometeotl/documentation/class-reference/model/spaces/space/), and [Action](/ometeotl/documentation/class-reference/model/actions/action/).
2. Register objects in [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/) through [World](/ometeotl/documentation/class-reference/model/world/world/).
3. Place object-space memberships in [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/).
4. Add space-to-space edges in [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/).
5. Serialize deterministically with `to_dict()` methods (canonical sorting for stable diffs).
6. Rebuild canonical objects with `from_dict()` methods.
7. Generate actor-relative snapshots via [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/) into [Perception](/ometeotl/documentation/class-reference/model/perception/perception/).
8. Derive first-order projection assumptions and projected successor perceived states from candidate actions, one [Perception](/ometeotl/documentation/class-reference/model/perception/perception/), and available resources through [DefaultProjectionTool](/ometeotl/documentation/class-reference/model/projection/default-projection-tool/).
9. Build a perception-driven [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/) with [build_linear_strategy(...)](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/strategies.py) or [build_branching_strategy(...)](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/strategies.py).
10. Validate payloads/objects with the staged validation pipeline in `ometeotl_core.validation` (syntactic, structural, temporal, spatial, admissibility, epistemic, completeness), using policy profiles (`observe_only`, `enforce_structure`, `enforce_domain`) when needed.
11. Export a world to canonical JSON or YAML via `ometeotl_core.io` ([world_to_json](/ometeotl/documentation/class-reference/io/world-export/), [world_to_yaml](/ometeotl/documentation/class-reference/io/world-export/), [write_world_json](/ometeotl/documentation/class-reference/io/world-export/), [write_world_yaml](/ometeotl/documentation/class-reference/io/world-export/)).
12. Re-import a world from JSON or YAML with validated reconstruction via [world_from_json / world_from_yaml](/ometeotl/documentation/class-reference/io/world-import/), which runs syntactic then structural validation before calling `World.from_dict`.
13. Optionally enforce command gating with [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/).
14. Represent actor objectives with [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) and optionally decompose them with [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/).
15. Link [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/) to a goal and evaluate admissibility with [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/).
16. Evaluate strategy outcomes with a [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/) implementation and rank with [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/).

Operationally, [World](/ometeotl/documentation/class-reference/model/world/world/) composes three independent graphs/registries:

- membership topology: [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/)
- spatial topology: [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
- object identity and lookup: [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/)

This separation prevents layer mixing and aligns with the architecture constraints in [specs_EN.md](https://github.com/kakchouch/ometeotl/blob/main/specs_EN.md).

## Test Layout

The test suite follows the same layer separation as the source tree:

- `tests/ometeotl_core/model/`: tests for `ometeotl_core.model.*`
- `tests/ometeotl_core/core/`: tests for `ometeotl_core.core.*`
- `tests/ometeotl_core/validation/`: tests for `ometeotl_core.validation.*`
- `tests/ometeotl_core/game/`: tests for `ometeotl_core.game.*`
- `tests/ometeotl_core/io/`: tests for `ometeotl_core.io.*`

Within each layer folder, tests are split by module using one file per module (`test_<module>.py`).

Run the complete suite from the repository root in one command:

- `pytest`

## Expert View

At expert level, the core implementation can be read as a set of deterministic state-transition boundaries.

### 1. Canonical object schema boundary

Every serializable entity normalizes to canonical JSON dictionaries:

- base schema from [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)
- extended schema in [Action](/ometeotl/documentation/class-reference/model/actions/action/), [World](/ometeotl/documentation/class-reference/model/world/world/), and [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)

Deterministic ordering is enforced by canonical sort helpers and sorted list serialization, making snapshots stable for audit/diff workflows.

### 2. Ontology boundary vs epistemic boundary

The ontology layer is [World](/ometeotl/documentation/class-reference/model/world/world/), [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/), [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/), and [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/).

The epistemic layer is [Perception](/ometeotl/documentation/class-reference/model/perception/perception/), [PerceivedSpace](/ometeotl/documentation/class-reference/model/perception/perceived-space/), [PerceivedMembership](/ometeotl/documentation/class-reference/model/perception/perceived-membership/), and [PerceivedRelation](/ometeotl/documentation/class-reference/model/perception/perceived-relation/), created by [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/) through composable [CoverageRule](/ometeotl/documentation/class-reference/model/sensor/coverage-rule/) and [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/).

Perceived actor composition is represented explicitly through [PerceivedComponentLink](/ometeotl/documentation/class-reference/model/perception/perceived-component-link/), which lets perceived hierarchies diverge from ontological hierarchies without mixing layers.

This realizes reality/perception dissociation from the spec: decisions can be based on perceived states, not only ontological states.

### 3. Authority boundary

When authority mode is enabled in [World](/ometeotl/documentation/class-reference/model/world/world/), direct mutations require a token.

[AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/) provides a single command path that enforces:

- command allowlisting
- command id deduplication
- actor existence checks
- strictly increasing sequence checks per actor
- bounded in-memory tracking for processed ids and sequence history
- immutable audit traces with [AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/)
- staged validation with configurable hardening profiles (`observe_only`, `enforce_structure`, `enforce_domain`)
- structured validation summaries attached to command results and audit entries

### 4. Extensibility seam

Primary extension seams are intentionally abstract and composable:

- [CoverageRule](/ometeotl/documentation/class-reference/model/sensor/coverage-rule/) and [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/) for sensing behavior
- custom object reconstruction factories through registry helpers and authority handlers
- custom command handlers injected into [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/)

### 5. Runtime wiring

[RuntimeContext](/ometeotl/documentation/class-reference/core/runtime-context/) plus `build_runtime(...)` provide explicit mode selection:

- local mode: direct world mutation APIs
- server-authoritative mode: command-gated mutation via [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/)

When server-authoritative mode is enabled, runtime also wires validation policy options (`validation_soft_gate`, `validation_policy_profile`, `validation_stage_mode_overrides`, `validation_block_on_error`, `validation_completeness_level`) through to the authority boundary.

This keeps local testing ergonomics while preserving an enforceable server boundary for multi-client systems.

### 6. First-order projection seam

[DefaultProjectionTool](/ometeotl/documentation/class-reference/model/projection/default-projection-tool/) is intentionally separate from the strategy model layer.

It consumes [Action](/ometeotl/documentation/class-reference/model/actions/action/), [Perception](/ometeotl/documentation/class-reference/model/perception/perception/), and [Resource](/ometeotl/documentation/class-reference/model/resources/resource/) inputs and emits [ProjectionAssumption](/ometeotl/documentation/class-reference/model/projection/projection-assumption/) collections grouped as [ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/) or [ProjectionBatch](/ometeotl/documentation/class-reference/model/projection/projection-batch/), together with a [ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/) representing the successor perceived state for that action.

This keeps first-order projection focused on assumption building plus successor-state derivation, while leaving later strategy-node construction and branching as a separate concern.

### 7. Strategy chaining seam

The strategy layer is implemented in [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/), [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/), [StrategyOutcomeBranch](/ometeotl/documentation/class-reference/model/strategies/strategy-outcome-branch/), and [StrategyBuildStep](/ometeotl/documentation/class-reference/model/strategies/strategy-build-step/).

The important rule is that a strategy node is anchored to:

- one action id
- one source perception id
- one projected successor perceived state

`validate_tree()` enforces that a child node must consume the parent node's projected successor perception when a branch links the two nodes.

This makes strategy hops explicitly perception-driven rather than action-list driven.

### 8. Builder seam

Two minimal builders exist today in `src/ometeotl_core/model/strategies.py`:

- `build_linear_strategy(...)` for ordered action sequences
- `build_branching_strategy(...)` for recursive action trees built from [StrategyBuildStep](/ometeotl/documentation/class-reference/model/strategies/strategy-build-step/)

Both builders project each action from the currently active perceived state and pass the resulting successor perceived state to the next node or subtree.

The current implementation intentionally keeps one projected successor perceived state per node.
Future support for one-action-to-many-outcomes branching is tracked as a TODO in the strategy layer, with the preferred direction being branch-specific projected outcomes on [StrategyOutcomeBranch](/ometeotl/documentation/class-reference/model/strategies/strategy-outcome-branch/).

### 9. Teleology and game utility seam

The teleology seam is now explicit in the model layer through [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) and [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/), while goal evaluation remains domain-neutral via [GoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-tool/) and [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/).

The game utility seam is explicit in [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/) plus concrete game-layer combinators [WeightedSumUtility](/ometeotl/documentation/class-reference/game/utility/weighted-sum-utility/) and [LexicographicUtility](/ometeotl/documentation/class-reference/game/utility/lexicographic-utility/).

[StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/) evaluates terminal projected states and aggregates branch probabilities in a deterministic way, including directed acyclic strategy graphs with merged terminal paths.
