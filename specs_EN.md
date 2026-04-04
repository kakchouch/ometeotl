## 0 — Purpose

**0-1. Project objective**: the library must make it possible to represent, generate, validate, serialize, and exploit multi-actor, multi-space, and multi-metric systems.
**0-2. Nature of the core**: the core must be abstract, agnostic, extensible, and minimally teleological; it must not impose any substantive objective on the model.
**0-3. Target domains**: the library must be usable in simulation, symbolic AI, generative AI, strategic games, synthetic worlds, and structural analysis.

## P — Principles

**P-1. Teleological neutrality**: no concrete purpose must be imposed by the core.
**P-2. Extensibility**: new spaces, metrics, actors, rules, and formats must be addable without structural breakage.
**P-3. Multi-space**: an actor or a resource must be able to exist in several spaces simultaneously.
**P-4. Hierarchy and emergence**: an actor must be able to contain other actors or emerge from perceived, real, or projected properties.
**P-5. Reality/perception dissociation**: decisions must depend on perception, not necessarily on ontological reality.
**P-6. Text interoperability**: every object in the system must be exportable to a text format usable by AI systems.

## A — Axioms

**A-1. Existence**: there are objects in the model; an object is any distinguishable and representable entity.
**A-2. Temporality**: every object, actor, resource, and attribute exists in time; time is ordered, irreversible, and common to the model.
**A-3. Spaces of existence**: every object exists in one or more spaces of existence, physical or abstract, whose validity depends on time.
**A-4. Actor**: an actor is an object capable of perception, decision, and action.
**A-5. Finitude**: every actor is finite in time, space, resources, and cognitive capacities.
**A-6. Resources**: an actor’s resources are objects with their own spaces of existence, and may consist of objects, actors, or both.
**A-7. Composition**: an actor may contain sub-actors with distinct attributes, constraints, and intentions.
**A-8. Reality of the model**: the past of the model is ontologically certain at the system level.
**A-9. Partial perception**: each actor has its own partial, biased, and potentially erroneous perception of the past, present, and future.
**A-10. Reality/perception dissociation**: actors’ decisions depend on their perception, not on the ontological reality of the model.
**A-11. Manipulability of perceptions**: perceptions can be modified by action, noise, forgetting, or informational transformation.
**A-12. Objectives**: an actor may have objectives concerning its own space of existence, that of others, its resources, or its continuity.
**A-13. Final and intermediate objectives**: final objectives may be stable and distant; intermediate objectives emerge dynamically from the perceived state of the world, resources, and competition.
**A-14. Capacity for conception**: an actor can only formulate or pursue objectives that it is capable of conceiving and sustaining in light of its resources, constraints, values, and horizon.
**A-15. Coexistence**: two actors can interact only if they coexist in time and share at least one relevant space of existence.
**A-16. Emergent conflict**: conflict can emerge from mere coexistence, without prior hostile intent, if spaces, resources, or objectives overlap.
**A-17. Harm**: harming an actor consists in reducing one or more dimensions of its space of existence toward null or critical values.
**A-18. Emergence of actors**: actors may emerge from other actors, from perceived properties, or from projections, even without full formal existence.
**A-19. Multiplicity of spaces**: spaces of existence may be physical, informational, symbolic, social, cognitive, legal, digital, or conceptual, and new spaces may emerge.
**A-20. Structural isomorphism**: actions of radically different nature may be considered equivalent if they produce structurally analogous effects on relevant metrics.
**A-21. Heterogeneous metrics**: effects are described by vectors of quantitative, qualitative, subjective, symbolic, or physical metrics, with no imposed common unit.
**A-22. Interpretive framework**: any global optimum exists only relative to an explicit interpretive framework defining objectives, weights, values, and constraints.
**A-23. Teleological neutrality**: the model presupposes no concrete goal; it provides a structure for representation, comparison, and evaluation.

## G — Game Theory

**G-1. Actors → players**: each actor in the model can be projected as a player in a game.
**G-2. Admissible actions → available strategies**: the set of actions compatible with resources, constraints, time, and space forms the set of admissible strategies.
**G-3. World state → game state**: the multi-space configuration of actors, resources, and perceptions defines the current game state.
**G-4. Partial perception → imperfect information**: games derived from the model are naturally games with incomplete or imperfect information.
**G-5. Intermediate objectives → subgames / stages**: intermediate objectives structure strategic trajectories as successive subgames.
**G-6. Heterogeneous metrics → multi-criteria utility functions**: utilities are not given a priori; they are derived from metrics through an interpretive framework.
**G-7. Conflict through coexistence → strategic competition**: mere coexistence in a shared space is enough to generate a potential competitive game.
**G-8. Limited resources → constraints and rivalries**: strategic rivalry may arise from overlap in resource spaces of existence, even without initial hostility.
**G-9. Reduction of the adversary’s space of existence → strategic gain/loss**: harming an opponent amounts to reducing their useful space of existence, which naturally translates into game utilities.
**G-10. Irreversible time → path-dependent dynamic games**: time irreversibility imposes a sequential, historical, and path-dependent reading of interactions.
**G-11. Uncertain future → optimization under projection**: an actor does not optimize a certain future, but a transition between a known past and an anticipated future.
**G-12. Internal hierarchy → nested games / internal coordination**: a composite actor may itself contain subgames of alignment, leadership, or coordination.

## F — Functional Requirements

**F-1. Canonical serialization**: all core objects must implement a canonical serialization protocol.
**F-2. Canonical format**: the reference format must be JSON; YAML must be supported as a secondary view.
**F-3. Minimum metadata**: each export must contain at least `id`, `type`, `schema_version`, `attributes`, `relations`, `state`, `context`, `provenance`.
**F-4. Cross-references**: cycles and cross-relations must be exported through identifier references, not infinite duplication.
**F-5. LLM/SLM view**: a dedicated language-model view must explicitly distinguish reality, perception, belief, hypothesis, and projection.
**F-6. Determinism**: exports must be deterministic and diffable.
**F-7. Schema validation**: exports must be schema-validatable.
**F-8. Versioning**: any schema break must trigger a version change.
**F-9. Syntactic validation**: the library must validate JSON/YAML documents.
**F-10. Structural validation**: the library must validate types, fields, relations, and hierarchies.
**F-11. Temporal validation**: the library must prevent any interaction outside temporal coexistence.
**F-12. Spatial/contextual validation**: the library must prevent any interaction without a relevant shared space.
**F-13. Admissibility validation**: the library must prevent the generation of intermediate objectives or strategies outside capabilities.
**F-14. Epistemic validation**: the library must make the status of perceptions explicit and allow the coexistence of errors, hypotheses, and certainties.
**F-15. Minimum completeness**: the library must reject or flag any instantiable object that is incomplete beyond a defined threshold.
**F-16. Contextual construction**: the library must allow the construction of worlds, actors, perceptions, resources, or strategies from a context.
**F-17. Generation protocol**: the library must provide a `from_context` protocol for generable objects.
**F-18. Generation pipeline**: the library must support the pipeline `context -> text generation -> parsing -> validation -> instantiation`.
**F-19. Partial generation**: the library must allow partial, incremental, or corrective generation.
**F-20. Explicit uncertainty**: the library must allow the generation of incomplete worlds with explicit uncertainty zones.
**F-21. Hybrid generation**: the library must allow rule-based symbolic generation and structured-prompt generative generation.
**F-22. Repair**: the library must be able to propose repairs or diagnostics in case of validation failure.
**F-23. Modularity**: the library must be organized around an abstract core and complementary modules.
**F-24. Separation of responsibilities**: the model, validation, export, generation, and game theory must be separated into distinct layers.
**F-25. Directory structure**: the project must follow a clear structure including `model/`, `game/`, `io/`, `validation/`, `generation/`, and `examples/`.
**F-26. Minimum interfaces**: the interfaces `Serializable`, `Validatable`, `LLMExportable`, `ContextualBuildable`, `Strategy`, and `UtilityFunction` must exist.
**F-27. Demo world**: the system must allow instantiating a coherent small world with several actors, spaces, and resources.
**F-28. Full export**: the system must support export to JSON and YAML.
**F-29. Re-import**: the system must support re-import without essential structural loss.
**F-30. Motivated rejection**: the system must reject an incoherent world with an explicit diagnosis.
**F-31. Minimal generation**: the system must generate at least one actor and one strategy from a context.
**F-32. Minimal game**: the system must produce a simple game instance with relative utilities.
**F-33. Ontological statuses**: the system must clearly document the real, perceived, hypothetical, and emergent statuses.
**F-34. Implementation priority**: V1 must prove the full chain representation → validation → export → generation → game.
**F-35. Minimal core**: V1 must first deliver the abstract core, canonical JSON, YAML, basic validation, minimal contextual generation, and a minimal game-theory interface.
**F-36. Reference examples**: V1 must include at least two examples: a simple world and a hierarchical multi-actor case.

## V1 priority

V1 must first demonstrate the system core with a reduced but complete scope: abstract core, canonical serialization, validation, minimal generation, and projection into game theory. The goal is to validate the end-to-end chain before adding mathematical refinements, more sophisticated solvers, or advanced features.

### V1 priorities

1. Abstract core of the model objects.
2. Canonical JSON + YAML.
3. Base-level full validation system.
4. Minimal contextual generation.
5. Minimal game-theory interface.
6. Two examples: a simple world and a hierarchical multi-actor case.

## Implementation

Here is a first architecture:

```text
project/
├── pyproject.toml
├── README.md
├── src/
│   └── masm/
│       ├── __init__.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── ids.py
│       │   ├── types.py
│       │   ├── time.py
│       │   ├── errors.py
│       │   └── protocols.py
│       │
│       ├── model/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── objects.py
│       │   ├── actors.py
│       │   ├── resources.py
│       │   ├── spaces.py
│       │   ├── actions.py
│       │   ├── metrics.py
│       │   ├── perception.py
│       │   ├── goals.py
│       │   ├── emergence.py
│       │   ├── world_state.py
│       │   └── relations.py
│       │
│       ├── validation/
│       │   ├── __init__.py
│       │   ├── result.py
│       │   ├── structural.py
│       │   ├── temporal.py
│       │   ├── spatial.py
│       │   ├── epistemic.py
│       │   ├── admissibility.py
│       │   └── pipeline.py
│       │
│       ├── io/
│       │   ├── __init__.py
│       │   ├── schema.py
│       │   ├── serializable.py
│       │   ├── json_codec.py
│       │   ├── yaml_codec.py
│       │   ├── llm_codec.py
│       │   └── registry.py
│       │
│       ├── generation/
│       │   ├── __init__.py
│       │   ├── context.py
│       │   ├── builders.py
│       │   ├── prompts.py
│       │   ├── parser.py
│       │   ├── repair.py
│       │   └── pipeline.py
│       │
│       ├── game/
│       │   ├── __init__.py
│       │   ├── strategies.py
│       │   ├── utility.py
│       │   ├── game_state.py
│       │   ├── transforms.py
│       │   ├── dominance.py
│       │   └── equilibrium.py
│       │
│       └── examples/
│           ├── __init__.py
│           ├── simple_world.py
│           └── hierarchical_world.py
│
└── tests/
    ├── test_model.py
    ├── test_validation.py
    ├── test_io.py
    ├── test_generation.py
    └── test_game.py
```