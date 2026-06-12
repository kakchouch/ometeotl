# Goals and specs
## 0 — Purpose

- **0-1. Project objective** the library must make it possible to represent, generate, validate, serialize, and exploit multi-actor, multi-space, and multi-metric systems.
- **0-2. Nature of the core** the core must be abstract, agnostic, extensible, and minimally teleological; it must not impose any substantive objective on the model.
- **0-3. Target domains** the library must be usable in simulation, symbolic AI, generative AI, strategic games, synthetic worlds, and structural analysis.

## P — Principles

- **P-1. Teleological neutrality** no concrete purpose must be imposed by the core.
- **P-2. Extensibility** new spaces, metrics, actors, rules, and formats must be addable without structural breakage.
- **P-3. Multi-space** an actor or a resource must be able to exist in several spaces simultaneously.
- **P-4. Hierarchy and emergence** an actor must be able to contain other actors or emerge from perceived, real, or projected properties.
- **P-5. Reality/perception dissociation** decisions must depend on perception, not necessarily on ontological reality.
- **P-6. Text interoperability** every object in the system must be exportable to a text format usable by AI systems.

## A — Axioms

- **A-1. Existence** there are objects in the model; an object is any distinguishable and representable entity.
- **A-2. Temporality** every object, actor, resource, and attribute exists in time; time is ordered, irreversible, and common to the model.
- **A-3. Spaces of existence** every object exists in one or more spaces of existence, physical or abstract, whose validity depends on time.
- **A-4. Actor** an actor is an object capable of perception, decision, and action.
- **A-5. Finitude** every actor is finite in time, space, resources, and cognitive capacities.
- **A-6. Resources** an actor’s resources are objects with their own spaces of existence, and may consist of objects, actors, or both.
- **A-7. Composition** an actor may contain sub-actors with distinct attributes, constraints, and intentions.
- **A-8. Reality of the model** the past of the model is ontologically certain at the system level.
- **A-9. Partial perception** each actor has its own partial, biased, and potentially erroneous perception of the past, present, and future.
- **A-10. Reality/perception dissociation** actors’ decisions depend on their perception, not on the ontological reality of the model.
- **A-11. Manipulability of perceptions** perceptions can be modified by action, noise, forgetting, or informational transformation.
- **A-12. Objectives** an actor may have objectives concerning its own space of existence, that of others, its resources, or its continuity.
- **A-13. Final and intermediate objectives** final objectives may be stable and distant; intermediate objectives emerge dynamically from the perceived state of the world, resources, and competition.
- **A-14. Capacity for conception** an actor can only formulate or pursue objectives that it is capable of conceiving and sustaining in light of its resources, constraints, values, and horizon.
- **A-15. Coexistence** two actors can interact only if they coexist in time and share at least one relevant space of existence.
- **A-16. Emergent conflict** conflict can emerge from mere coexistence, without prior hostile intent, if spaces, resources, or objectives overlap.
- **A-17. Harm** harming an actor consists in reducing one or more dimensions of its space of existence toward null or critical values.
- **A-18. Emergence of actors** actors may emerge from other actors, from perceived properties, or from projections, even without full formal existence.
- **A-19. Multiplicity of spaces** spaces of existence may be physical, informational, symbolic, social, cognitive, legal, digital, or conceptual, and new spaces may emerge.
- **A-20. Structural isomorphism** actions of radically different nature may be considered equivalent if they produce structurally analogous effects on relevant metrics.
- **A-21. Heterogeneous metrics** effects are described by vectors of quantitative, qualitative, subjective, symbolic, or physical metrics, with no imposed common unit.
- **A-22. Interpretive framework** any global optimum exists only relative to an explicit interpretive framework defining objectives, weights, values, and constraints.
- **A-23. Teleological neutrality** the model presupposes no concrete goal; it provides a structure for representation, comparison, and evaluation.
- **A-24. Emerging irrationality** goals and strategies are valid for an actor only according to their perceptions, projections and belief, independently of the world ontological reality.
## G — Game Theory

- **G-1. Actors → players** each actor in the model can be projected as a player in a game.
- **G-2. Admissible actions → available strategies** the set of actions compatible with resources, constraints, time, and space forms the set of admissible strategies.
- **G-3. World state → game state** the multi-space configuration of actors, resources, and perceptions defines the current game state.
- **G-4. Partial perception → imperfect information** games derived from the model are naturally games with incomplete or imperfect information.
- **G-5. Intermediate objectives → subgames / stages** intermediate objectives structure strategic trajectories as successive subgames.
- **G-6. Heterogeneous metrics → multi-criteria utility functions** utilities are not given a priori; they are derived from metrics through an interpretive framework.
- **G-7. Conflict through coexistence → strategic competition** mere coexistence in a shared space is enough to generate a potential competitive game.
- **G-8. Limited resources → constraints and rivalries** strategic rivalry may arise from overlap in resource spaces of existence, even without initial hostility.
- **G-9. Reduction of the adversary’s space of existence → strategic gain/loss** harming an opponent amounts to reducing their useful space of existence, which naturally translates into game utilities.
- **G-10. Irreversible time → path-dependent dynamic games** time irreversibility imposes a sequential, historical, and path-dependent reading of interactions.
- **G-11. Uncertain future → optimization under projection** an actor does not optimize a certain future, but a transition between a known past and an anticipated future.
- **G-12. Internal hierarchy → nested games / internal coordination** a composite actor may itself contain subgames of alignment, leadership, or coordination.

## F — Functional Requirements

- **F-1. Canonical serialization** all core objects must implement a canonical serialization protocol.
- **F-2. Canonical format** the reference format must be JSON; YAML must be supported as a secondary view.
- **F-3. Minimum metadata** each export must contain at least `id`, `type`, `schema_version`, `attributes`, `relations`, `state`, `context`, `provenance`.
- **F-4. Cross-references** cycles and cross-relations must be exported through identifier references, not infinite duplication.
- **F-5. LLM/SLM view** a dedicated language-model view must explicitly distinguish reality, perception, belief, hypothesis, and projection.
- **F-6. Determinism** exports must be deterministic and diffable.
- **F-7. Schema validation** exports must be schema-validatable.
- **F-8. Versioning** any schema break must trigger a version change.
- **F-9. Syntactic validation** the library must validate JSON/YAML documents.
- **F-10. Structural validation** the library must validate types, fields, relations, and hierarchies.
- **F-11. Temporal validation** the library must prevent any interaction outside temporal coexistence.
- **F-12. Spatial/contextual validation** the library must prevent any interaction without a relevant shared space.
- **F-13. Admissibility validation** the library must prevent the generation of intermediate objectives or strategies outside of the actors own perceived capabilities.
- **F-14. Epistemic validation** the library must make the status of perceptions explicit and allow the coexistence of errors, hypotheses, and certainties.
- **F-15. Minimum completeness** the library must reject or flag any instantiable object that is incomplete beyond a defined threshold.
- **F-16. Contextual construction** the library must allow the construction of worlds, actors, perceptions, resources, or strategies from a context.
- **F-17. Generation protocol** the library must provide a `from_context` protocol for generable objects.
- **F-18. Generation pipeline** the library must support the pipeline `context -> text generation -> parsing -> validation -> instantiation`.
- **F-19. Partial generation** the library must allow partial, incremental, or corrective generation.
- **F-20. Explicit uncertainty** the library must allow the generation of incomplete worlds with explicit uncertainty zones.
- **F-21. Hybrid generation** the library must allow rule-based symbolic generation and structured-prompt generative generation.
- **F-22. Repair** the library must be able to propose repairs or diagnostics in case of validation failure.
- **F-23. Modularity** the library must be organized around an abstract core and complementary modules.
- **F-24. Separation of responsibilities** the model, validation, export, generation, and game theory must be separated into distinct layers.
- **F-25. Directory structure** the project must follow a clear structure including `model/`, `game/`, `io/`, `validation/`, `generation/`, and `examples/`.
- **F-26. Minimum interfaces** the interfaces `Serializable`, `Validatable`, `LLMExportable`, `ContextualBuildable`, `Strategy`, and `UtilityFunction` must exist.
- **F-27. Demo world** the system must allow instantiating a coherent small world with several actors, spaces, and resources.
- **F-28. Full export** the system must support export to JSON and YAML.
- **F-29. Re-import** the system must support re-import without essential structural loss.
- **F-30. Motivated rejection** the system must reject an incoherent world with an explicit diagnosis.
- **F-31. Minimal generation** the system must generate at least one actor and one strategy from a context.
- **F-32. Minimal game** the system must produce a simple game instance with relative utilities.
- **F-33. Ontological statuses** the system must clearly document the real, perceived, hypothetical, and emergent statuses.
- **F-34. Implementation priority** V1 must prove the full chain representation → validation → export → generation → game.
- **F-35. Minimal core** V1 must first deliver the abstract core, canonical JSON, YAML, basic validation, minimal contextual generation, and a minimal game-theory interface.
- **F-36. Reference examples** V1 must include at least two examples: a simple world and a hierarchical multi-actor case.

## V1 priority

V1 must first demonstrate the system core with a reduced but complete scope: abstract core, canonical serialization, validation, minimal generation, and projection into game theory. The goal is to validate the end-to-end chain before adding mathematical refinements, more sophisticated solvers, or advanced features.

### V1 priorities

1. Abstract core of the model objects.
2. Canonical JSON + YAML.
3. Base-level full validation system.
4. Minimal contextual generation.
5. Minimal game-theory interface.
6. Two examples: a simple world and a hierarchical multi-actor case.

## Current repository state (June 2026)

The repository now contains a broader functional V1-incremental core spanning model, perception, projection, strategy, and authority/runtime boundaries.

**04/25/26 - major architectural overhaul:**
  Local tests reveal the current architecture is too abstract for any practical implementation. It has been decided to :
  - to keep the current code in a core module `ometeotl_core`, which is intended to remain abstract;
  - to add a primary layer of specialization `ometeotl_foundations`, including  :
    - spatial: primary layer of spatial implementation of `ometeotl_core`;
    - networks: primary layer of graph theory implementation of `ometeotl_core`
    - ...
  - to add, lastly, an adapter layer `ometeotl_adapters`, which implements each specialization layer with a reputable library.


### Implemented and tested now

1. Core object model in `src/ometeotl_core/model/`:
	- `ModelObject`, `GenericObject`, `Actor`, `Resource`, `Space`, `World`.
	- `WorldModelRegistry` and reconstruction helpers.
2. Spatial structures:
	- `SpaceObjectGraph` and `SpaceObjectMembership`.
	- `SpaceRelation`, `SpaceRelationType`, and `SpaceRelationGraph` with canonicalization and relation constraints.
3. Actor hierarchy and abstraction:
	- Composition modes and explicit `component` relations on actors.
	- Cycle detection, tree resolution, parent lookup, and abstract hierarchy helpers.
	- Abstract spaces through `Space.is_abstract`.
4. Perception layer:
	- `Perception`, `PerceivedSpace`, `PerceivedMembership`, `PerceivedRelation`, `PerceivedComponentLink`.
	- Epistemic status validation and deterministic serialization of perceived structures.
5. Sensor pipeline:
	- `CoverageRule` and `NoiseRule` abstractions.
	- `TotalCoverageRule` and `IdentityNoiseRule` defaults.
	- Timestamp-aware and deterministic perception id behavior.
6. Projection and strategy layers:
	- `ProjectionAssumption`, `ProjectedPerceptionChange`, `ProjectedPerceptionState`, `ActionProjection`, `ProjectionBatch`.
	- `DefaultProjectionTool`, `Strategy`, `StrategyNode`, `StrategyOutcomeBranch`, `StrategyBuildStep`.
	- `build_linear_strategy(...)` and `build_branching_strategy(...)` builders driven by projected successor perceptions; projected states carried by `StrategyOutcomeBranch`, enabling one action to emit distinct outcomes per branch.
7. Teleology and utility layers:
	- `Goal`, `GoalBuildStep`, `GoalDecompositionTree`.
	- `GoalFeasibilityTool`, `DefaultGoalFeasibilityTool`, `GoalAdmissibilityChecker`.
	- `UtilityFunction`, `UtilityFrame`, `WeightedSumUtility`, `LexicographicUtility`, `StrategyRanker`.
8. Core runtime infrastructure:
	- `AuthorityCommandHandler`, `CommandEnvelope`, `CommandResult`, `AuditEntry`.
	- `RuntimeContext` and `build_runtime(...)`.
9. Validation layer in `src/ometeotl_core/validation/`:
	- Validation contracts and staged pipeline.
	- Validator families: syntactic, structural, temporal, spatial, admissibility, epistemic, completeness.
	- Policy profiles: `observe_only`, `enforce_structure`, `enforce_domain`.
	- Diagnostics and repair suggestions.
10. IO layer in `src/ometeotl_core/io/`:
	- Canonical JSON and YAML world export (`world_to_json`, `world_to_yaml`, `write_world_json`, `write_world_yaml`).
	- Validated world import (`world_from_json`, `world_from_yaml`, `WorldImportResult`).
	- LLM/SLM view exporter (`llm_export.py`): `world_to_llm_view`, `actor_to_llm_view`, `perception_to_llm_view`, and `ModelObject.to_llm_view()` with explicit reality/perception/belief/hypothesis/projection separation.
11. Generation layer in `src/ometeotl_core/generation/`:
	- `GenerationContext` declarative input dataclass with nested child contexts, placement instructions, constraint declarations, and `copy_with` for rule-safe mutation.
	- `ContextualBuilder` ABC with concrete builders for all core kinds (world, actor, strategy, goal, perception).
	- Pluggable `GenerationRule` / `GenerationRuleSet` / `RuleRegistry` rule engine with built-in constraint propagation (temporal, spatial, admissibility).
	- `LLMGenerationAdapter` for optional provider-agnostic LLM-assisted context refinement with fallback.
	- `ContextualGenerationPipeline` orchestrating rules → build → optional registration → optional validation → `GenerationResult`.
	- `from_context()` classmethods on `World`, `Actor`, `Strategy`, and `Goal`.
	- Four runnable demo scenarios in `generation/examples.py`.
12. **Spatial foundations layer** in `src/ometeotl_foundations/spatial/`:
	- Coordinate value types: `Coordinate2D`, `Coordinate3D`, `GeoCoordinate` (with range validation), `GridCell`.
	- Coordinate system vocabulary: `CoordinateKind` (str enum), `CoordinateSystem` with `to_dict`/`from_dict`, predefined singletons `CARTESIAN_2D`, `CARTESIAN_3D`, `WGS84`, `GRID`.
	- Structural protocols (`runtime_checkable`): `Geometry`, `SpatialIndex`, `SpatialBackend`.
	- `BoundingBox`: pure-Python frozen dataclass implementing `Geometry` with DE-9IM-correct `touches()`, `contains()`, `intersects()`, `distance()`, convenience methods (`expand`, `union`, `from_center`, `from_point`), and `to_dict`/`from_dict` round-trip.
	- `GeometricSpace[G]`: frozen generic dataclass composing a core `Space` with a concrete geometry; proxy properties (`id`, `kind`, `is_abstract`, `dimensions`); injected-deserializer `from_dict`.
	- `SpatialExtent[G]`: frozen generic dataclass recording an object's footprint/position within a named coordinate frame; injected-deserializer `from_dict`.
	- `SpatialMap[G]`: mutable generic container (CRUD + O(n) spatial queries `ids_containing_point`, `ids_intersecting`); subclassable for index-backed overrides.
	- `derive_space_relations()`: bridge function that derives a `SpaceRelationGraph` from geometry comparisons (containment → intersection → adjacency, with `skip_abstract`, `adjacency_tolerance`, and per-relation-type flags).
13. Quality gate:
	- Automated tests across `tests/ometeotl_core/` and `tests/ometeotl_foundations/spatial/`.
	- Current baseline: `586` collected tests.

### Still incomplete or planned

- `src/ometeotl_core/game/` for deeper solver-facing abstractions beyond current utility and ranking primitives.
- Generation integration testing: a full roundtrip test of the complete chain (context → pipeline → generated objects → IO export → `to_llm_view()` → parse → validate), and a concrete 2-actor game scenario exercising goal-strategy linkage with utility ranking.
- `examples/` further extended with additional end-to-end demo worlds (labs 2–10 and the strategy game demo are present; more are planned).
- **Networks foundations layer** (`src/ometeotl_foundations/networks/`): first-order graph-theory specialization of `ometeotl_core` — stub only, not yet implemented.
- **Shapely adapter** (`src/ometeotl_adapters/spatial_shapely/`): library-backed implementation of `SpatialBackend` and `SpatialIndex` using Shapely — stub only.
- **NetworkX adapter** (`src/ometeotl_adapters/networks_networkx/`): library-backed graph implementation — stub only.

### Current TODO priorities

1. Implement `ometeotl_foundations/networks/` (graph-theory specialization layer).
2. Implement `ometeotl_adapters/spatial_shapely/` (Shapely-backed `SpatialBackend` + `SpatialIndex`).
3. Add a full generation roundtrip integration test covering the complete chain: context → pipeline → generated objects → IO export → `to_llm_view()` → parse → validate. Add a concrete 2-actor game scenario wiring goals, strategies, and utility ranking end to end.
4. Extend the game layer beyond the current utility/ranking primitives with solver-facing structures.
5. Extend `examples/` with additional end-to-end demo worlds beyond the existing lab series.
