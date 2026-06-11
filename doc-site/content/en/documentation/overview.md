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
- [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/) anchors one action and its input perceived state to an ordered set of [StrategyOutcomeBranch](/ometeotl/documentation/class-reference/model/strategies/strategy-outcome-branch/) links; each branch carries its own projected successor perceived state
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/) groups nodes into a linear or branching perception-driven tree

Teleology, utility/ranking, and multi-actor game structures are now implemented as model and game extensions:

- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) and [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/) represent final or intermediate objectives and hierarchical decomposition.
- [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/) and [DefaultGoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/default-goal-feasibility-tool/) provide model-level feasibility and admissibility checks.
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/) defines the abstract utility contract.
- [WeightedSumUtility](/ometeotl/documentation/class-reference/game/utility/weighted-sum-utility/), [LexicographicUtility](/ometeotl/documentation/class-reference/game/utility/lexicographic-utility/), and [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/) provide game-layer utility derivation and strategy ranking over projected terminal states.
- [PlayerProfile](/ometeotl/documentation/class-reference/game/game-state/player-profile/) and [GameState](/ometeotl/documentation/class-reference/game/game-state/game-state/) bind actors to their admissible strategies and capture the multi-actor game snapshot.
- [NormalFormGame](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/) builds the full payoff matrix from a [GameState](/ometeotl/documentation/class-reference/game/game-state/game-state/) by enumerating all strategy profile combinations through a [PayoffFunction](/ometeotl/documentation/class-reference/game/normal-form/payoff-function/).
- [BestResponseCalculator](/ometeotl/documentation/class-reference/game/best-response/best-response-calculator/) finds the utility-maximising strategy for a focal actor against fixed opponent strategies.

Model objects can also be generated programmatically from declarative inputs:

- [GenerationContext](/ometeotl/documentation/class-reference/generation/generation-context/) is the declarative input carrying identity, attributes, nested child contexts, placements, and constraints.
- [ContextualGenerationPipeline](/ometeotl/documentation/class-reference/generation/pipeline/) orchestrates rule application, builder dispatch, optional registration, and optional validation.
- [GenerationRule / GenerationRuleSet / RuleRegistry](/ometeotl/documentation/class-reference/generation/rule-engine/) provide pluggable constraint propagation (temporal, spatial, admissibility).
- [LLMGenerationAdapter](/ometeotl/documentation/class-reference/generation/llm-integration/) enables optional LLM-assisted context refinement before building.
- `to_llm_view()` on any model object exports a language-model-oriented payload with explicit reality/perception separation ([LLM view export](/ometeotl/documentation/class-reference/io/llm-view-export/)).

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
13. Export any entity as a language-model-oriented payload via `to_llm_view()` ([LLM view export](/ometeotl/documentation/class-reference/io/llm-view-export/)), which separates ontological reality from epistemic/perception-aware views.
14. Optionally enforce command gating with [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/).
15. Represent actor objectives with [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) and optionally decompose them with [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/).
16. Link [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/) to a goal and evaluate admissibility with [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/).
17. Evaluate strategy outcomes with a [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/) implementation and rank with [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/).
18. Build a multi-actor game by wrapping players in [PlayerProfile](/ometeotl/documentation/class-reference/game/game-state/player-profile/) objects and grouping them into a [GameState](/ometeotl/documentation/class-reference/game/game-state/game-state/), then calling [NormalFormGame.from_game_state(...)](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/) with an [IndependentPayoffFunction](/ometeotl/documentation/class-reference/game/normal-form/independent-payoff-function/) to compute the full payoff matrix.
19. Find best responses with [BestResponseCalculator.compute(...)](/ometeotl/documentation/class-reference/game/best-response/best-response-calculator/) given fixed opponent strategies.
20. Generate model objects programmatically from declarative [GenerationContext](/ometeotl/documentation/class-reference/generation/generation-context/) inputs using [ContextualGenerationPipeline](/ometeotl/documentation/class-reference/generation/pipeline/), with optional constraint propagation via the [rule engine](/ometeotl/documentation/class-reference/generation/rule-engine/) and optional LLM-assisted context refinement via [LLMGenerationAdapter](/ometeotl/documentation/class-reference/generation/llm-integration/).

Operationally, [World](/ometeotl/documentation/class-reference/model/world/world/) composes three independent graphs/registries:

- membership topology: [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/)
- spatial topology: [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
- object identity and lookup: [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/)

This separation prevents layer mixing and aligns with the architecture constraints in [specs_EN.md](https://github.com/kakchouch/ometeotl/blob/main/specs_EN.md).

## Test Layout

The test suite follows the same layer separation as the source tree:

- `tests/ometeotl_core/model/`: tests for `ometeotl_core.model.*`
- `tests/ometeotl_core/generic/`: tests for `ometeotl_core.generic.*`
- `tests/ometeotl_core/validation/`: tests for `ometeotl_core.validation.*`
- `tests/ometeotl_core/game/`: tests for `ometeotl_core.game.*`
- `tests/ometeotl_core/io/`: tests for `ometeotl_core.io.*`
- `tests/ometeotl_core/generation/`: tests for `ometeotl_core.generation.*`

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

### 4. LLM export boundary

`to_llm_view()` is defined on [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/) and dispatches to [LLMViewBuilder](/ometeotl/documentation/class-reference/io/llm-view-export/) by object type.

The export path (F-5) keeps ownership clean:
- `model` owns canonical state (`to_dict` and domain classes)
- `io` owns formatting and projection for external consumers

Output always exposes explicit epistemic distinctions: `reality`, `perception`, `belief`, `hypothesis`, `projection`. Collections and epistemic groups are produced deterministically (sorted keys).

### 5. Generation boundary

The generation layer (F-16 to F-22) converts declarative [GenerationContext](/ometeotl/documentation/class-reference/generation/generation-context/) inputs into model objects through a deterministic pipeline:

```
GenerationContext
    → GenerationRuleSet.apply()   # constraint propagation, normalization
    → build_from_context()        # kind dispatch to builder functions
    → registration / validation   # optional; driven by context flags
    → GenerationResult
```

Key design properties:
- Rule application is purely functional: each rule receives a context and returns a new one via `copy_with`.
- [RuleRegistry](/ometeotl/documentation/class-reference/generation/rule-engine/) enables pluggable policy selection at call-site without modifying the pipeline.
- [LLMGenerationAdapter](/ometeotl/documentation/class-reference/generation/llm-integration/) is explicitly chained by callers — the pipeline never calls it automatically.
- Constraint propagation rules use `setdefault` semantics, making the pipeline non-destructive: existing metadata survives rule application.

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
- one source perception id (the perceived state the action is applied from)
- an ordered list of [StrategyOutcomeBranch](/ometeotl/documentation/class-reference/model/strategies/strategy-outcome-branch/) links, each carrying its own projected successor perceived state

`validate_tree()` enforces two invariants per branch:

1. if a branch's `projected_state` is present, its `generating_action_id` must match the parent node's `action_id`
2. if a branch links to a child node and carries a `projected_state`, the child node's `source_perception_id` must equal the branch's projected perception id

This makes strategy hops explicitly perception-driven and allows one action to produce several distinct outcomes across sibling branches.

### 8. Builder seam

Two minimal builders exist today in `src/ometeotl_core/model/strategies.py`:

- `build_linear_strategy(...)` for ordered action sequences
- `build_branching_strategy(...)` for recursive action trees built from [StrategyBuildStep](/ometeotl/documentation/class-reference/model/strategies/strategy-build-step/)

Both builders project each action from the currently active perceived state and attach the resulting successor perceived state to the outgoing branches of each node.

`build_branching_strategy(...)` allows one action to branch into several sibling child steps: all sibling branches from a node share the same parent action's projected state, while each child subtree is projected from that shared successor perception onward.

### 9. Teleology and game utility seam

The teleology seam is now explicit in the model layer through [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) and [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/), while goal evaluation remains domain-neutral via [GoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-tool/) and [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/).

The game utility seam is explicit in [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/) plus concrete game-layer combinators [WeightedSumUtility](/ometeotl/documentation/class-reference/game/utility/weighted-sum-utility/) and [LexicographicUtility](/ometeotl/documentation/class-reference/game/utility/lexicographic-utility/).

[StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/) evaluates terminal projected states and aggregates branch probabilities in a deterministic way, including directed acyclic strategy graphs with merged terminal paths.

The multi-actor game seam is implemented as three composable layers:

1. **Game state** — [PlayerProfile](/ometeotl/documentation/class-reference/game/game-state/player-profile/) binds an actor to its admissible strategies and utility function. [GameState](/ometeotl/documentation/class-reference/game/game-state/game-state/) groups players into a snapshot with a `world_id` reference, realizing G-1 (actors → players) and G-3 (world state → game state).

2. **Normal form** — [NormalFormGame.from_game_state(...)](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/) enumerates the Cartesian product of all players' strategy lists and evaluates each profile through a [PayoffFunction](/ometeotl/documentation/class-reference/game/normal-form/payoff-function/). The V1 concrete implementation, [IndependentPayoffFunction](/ometeotl/documentation/class-reference/game/normal-form/independent-payoff-function/), delegates per-player evaluation to [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/) — no logic is duplicated. The abstraction keeps the door open for joint-projection payoff functions without breaking callers.

3. **Best response** — [BestResponseCalculator.compute(...)](/ometeotl/documentation/class-reference/game/best-response/best-response-calculator/) operates on a prebuilt [NormalFormGame](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/), filters payoff vectors to rows where opponent strategies match, and returns the [BestResponseResult](/ometeotl/documentation/class-reference/game/best-response/best-response-result/) with the dominant strategy and a ranked list of all options. Tie-breaking is deterministic (descending utility, then ascending strategy id), consistent with the `rank_key` convention in [RankedStrategy](/ometeotl/documentation/class-reference/game/utility/ranked-strategy/).
