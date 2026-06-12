---
title: "Ometeotl: A Decision Meta-Model in Progress"
date: 2026-04-04
draft: false
---

# WORK IN PROGRESS - Under construction
<p align="center">
  <img src="/ometeotl/images/logo.png" width="300" height="300" alt="Ometeotl logo"/>
</p>

<big><b>Ometeotl</b> : _A Python library to build complex multi-agent simulations, wargames, and AI-driven strategies_</big>

_Create simulated worlds with competitive or cooperative entities using simple class instantiations. Define goals and strategies through clear, standard formats. Train AI agents to act, adapt, and compete in your world. Navigate through a natively built fog of war_

[Github repo](https://github.com/kakchouch/ometeotl#)

# Ometeotl: An experimental meta-model for complex decisional systems

**Ometeotl** is an experimental Python library for modeling multi-actor, multi-space, multi-metric strategic decision-making systems. Inspired by game theory, axiomatic systems, and neutral teleological modeling, it aims to simulate complex interactions across hierarchical actors, asymmetric temporalities, and perceptual imperfections.

## Cultural Inspiration

The name **Ometeotl** draws from Aztec mythology, where *Ōme* means "two" or "dual" in Nahuatl, and *teōtl* translates to "divinity." Ometeotl embodies the primordial duality—male (Ometecuhtli) and female (Omecihuatl)—as the supreme creator residing in Omeyocan, the "Place of Duality." This concept of inherent duality and generative potential mirrors the library's core philosophy: modeling conflict, cooperation, and emergence from opposing forces in decision spaces.

## Use Cases

- Advanced multi-agent simulations  
- Wargaming and strategic modeling  
- Decision-making benchmarks for symbolic and generative AI  
- Game development and interactive systems  

## Work in Progress

This project is **actively under development**. The current codebase implements a functional core covering modeling, perception, projection, strategy, teleology, game-layer utility ranking, composite actors, server-authoritative runtime boundaries, a dedicated validation layer, canonical IO (JSON/YAML), LLM-oriented export, and a complete contextual generation pipeline with pluggable rule engine and optional LLM-assisted refinement.

## Architectural Note (April 2026)

Local tests revealed that the current architecture is too abstract for direct practical implementation. It has been decided to:

- Keep the current code in the abstract core module `ometeotl_core`.
- Add a primary specialization layer `ometeotl_foundations`, covering:
  - **spatial** — primary spatial implementation of `ometeotl_core`
  - **networks** — primary graph-theory implementation of `ometeotl_core`
  - … (further domains planned)
- Add an adapter layer `ometeotl_adapters` that implements each specialization with a reputable third-party library.

## Current Status

As of June 2026, the repository includes:

- Full model core in `src/ometeotl_core/model/` with `ModelObject`, `GenericObject`, `Actor`, `Resource`, `Space`, `World`, and registry support.
- Spatial topology with `SpaceObjectGraph`, `SpaceObjectMembership`, `SpaceRelation`, and `SpaceRelationGraph`.
- Composite and abstract actor support with explicit `component` links, composition modes, cycle detection, hierarchy traversal, and abstract-space helpers.
- Sensor pipeline with `CoverageRule`, `NoiseRule`, `TotalCoverageRule`, `IdentityNoiseRule`, snapshot timestamp support, and deterministic perception IDs.
- Perception layer with `Perception`, `PerceivedSpace`, `PerceivedMembership`, `PerceivedRelation`, and `PerceivedComponentLink` with epistemic status validation.
- Projection layer with `ProjectionAssumption`, `ProjectedPerceptionChange`, `ProjectedPerceptionState`, `ActionProjection`, `ProjectionBatch`, and `DefaultProjectionTool`.
- Strategy layer with `Strategy`, `StrategyNode`, `StrategyOutcomeBranch`, `StrategyBuildStep`, `build_linear_strategy`, and `build_branching_strategy` — each outcome branch carries its own projected successor perceived state, enabling one action to emit distinct outcomes per branch.
- Teleology and utility layers with first-class `Goal` objects, decomposition trees, feasibility/admissibility tools (`GoalFeasibilityTool`, `GoalAdmissibilityChecker`), and `UtilityFunction`/`UtilityFrame`.
- Game layer in `src/ometeotl_core/game/` with `PlayerProfile`, `GameState`, `NormalFormGame`, `IndependentPayoffFunction`, `PayoffVector`, `BestResponseCalculator`, `WeightedSumUtility`, `LexicographicUtility`, and `StrategyRanker` — enabling payoff matrix construction and best-response reasoning over strategy profiles.
- Core runtime infrastructure in `src/ometeotl_core/generic/` with `AuthorityCommandHandler`, `CommandEnvelope`, `CommandResult`, `AuditEntry`, `RuntimeContext`, and `build_runtime`.
- Validation layer with staged `ValidationPipeline`, validator families (syntactic, structural, temporal, spatial, admissibility, epistemic, completeness), policy hardening profiles (`observe_only`, `enforce_structure`, `enforce_domain`), and `DiagnosticBuilder`.
- Minimum interfaces in `src/ometeotl_core/model/interfaces.py`: `Serializable`, `Validatable`, `LLMExportable`, `ContextualBuildable`.
- Canonical IO layer in `src/ometeotl_core/io/` with JSON/YAML world export and import plus a dedicated LLM/SLM view exporter (`world_to_llm_view`, `actor_to_llm_view`, `perception_to_llm_view`, `ModelObject.to_llm_view()`) that explicitly separates reality, perception, belief, hypothesis, and projection.
- Contextual generation pipeline in `src/ometeotl_core/generation/` with `GenerationContext`, class-based `ContextualBuilder` abstractions for all core kinds, pluggable `GenerationRule`/`GenerationRuleSet`/`RuleRegistry` rule engine with built-in constraint propagation (temporal, spatial, admissibility), `LLMGenerationAdapter`, and `ContextualGenerationPipeline` orchestrating rules → build → registration → validation → `GenerationResult`.
- `from_context()` classmethods on `World`, `Actor`, `Strategy`, and `Goal`; four runnable demo scenarios in `generation/examples.py`.
- **Spatial foundations layer** in `src/ometeotl_foundations/spatial/` — pure-Python, adapter-agnostic first-order specialization including coordinate value types (`Coordinate2D`, `Coordinate3D`, `GeoCoordinate`, `GridCell`), a coordinate system vocabulary (`CoordinateSystem`, `CoordinateKind`, predefined singletons `CARTESIAN_2D`, `WGS84`, `GRID`), structural protocols (`Geometry`, `SpatialIndex`, `SpatialBackend`), a pure-Python geometry primitive (`BoundingBox` with DE-9IM-correct `touches()`), generic typed spatial containers (`GeometricSpace[G]`, `SpatialExtent[G]`, `SpatialMap[G]`), and `derive_space_relations()` — the bridge that derives a `SpaceRelationGraph` from geometry comparisons.
- Complete class-reference documentation with code examples for all public classes across `ometeotl_core` and `ometeotl_foundations/spatial/`.
- Current automated baseline: `586` collected tests.

## Near-Term TODOs

- Extend reference examples in `examples/` with additional end-to-end demo worlds.

## Join the Journey

**All contributions are welcome!** Whether it's code refinements, axiom suggestions, documentation, testing, or cultural insights into the name's resonance, your input will shape Ometeotl. Check the [specs](goals_and_specs/_index.md), [README](https://github.com/kakchouch/ometeotl), or [CONTRIBUTING.md](https://github.com/kakchouch/ometeotl?tab=contributing-ov-file) to get started. Fork, PR, or open an issue—let's build this together.

**Start your first PR and become an Eagle Warrior !**

### Developer Ranks - The Path of the Serpent
The Path of the Serpent represents knowledge, depth, and commitment.  
It is the path of those who learn, refine, and wage a quiet, relentless struggle against bad code—both in the system and within themselves.

<table>
<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/1.eagle_warrior.png" width="110">
</td>
<td>

#### Eagle Warrior

**Requirement**  
First merged PR  

<br>

<small><i>
In Nahua warrior tradition, the eagle symbolizes courage, ascent, and the honor of proving oneself in action.
</i></small>

</td>
</tr>
<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/2.achcauhtli.png" width="125">
</td>
<td>

#### Achcauhtli

**Requirement**  
2 to 4 merged PR  

<br>

<small><i>
Achcauhtli evokes a proven war leader, a contributor who has moved beyond initiation and begun to earn standing through repeated service.
</i></small>

</td>
</tr>
<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/3.otomi.png" width="140">
</td>
<td>

#### Otomi

**Requirement**  
5 to 19 merged PR  

<br>

<small><i>
The Otomi warrior figure represents resilience and battlefield reputation, honoring contributors who have become dependable forces within the project.
</i></small>

</td>
</tr>
<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/4.shorn_one.png" width="140">
</td>
<td>

#### Shorn One

**Requirement**  
20+ merged PR  

<br>

<small><i>
The Shorn Ones were elite warriors sworn not to retreat, making this rank a symbol of exceptional discipline, loyalty, and sustained achievement.
</i></small>

</td>
</tr>
<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/5.emperor.png" width="140">
</td>
<td>

#### Emperor

**Requirement**  
Founder and principal Maintainer.

<br>

<small><i>
The Emperor stands as the sovereign guardian of the Order, embodying stewardship, vision, and the sacred balance at the heart of Ometeotl.
</i></small>

</td>
</tr>
</table>

### Community Benefactors - The Path of the Undying Sun
The Path of the Undying Sun represents clarity, guidance, and transmission.  
It is the path of those who illuminate the way for others and sustain the living flame of knowledge.

<table>
<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/p1_tlamacazqui.png" width="110">
</td>
<td>

#### Tlamacazqui - Initiate

**Requirement**  
Notable contribution to the community

<br>

<small><i>
Those who begin to carry the light and make their presence felt.
</i></small>

</td>
</tr>
<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/p2_tlenemacac.png" width="120">
</td>
<td>

#### Tlenamacac - Officiant

**Requirement**  
Significant contribution to the community

<br>

<small><i>
Those who sustain the flame and help it grow beyond themselves.
</i></small>

</td>
</tr>
<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/p3_high_priest.png" width="140">
</td>
<td>

#### Quetzalcoatl Priest
_High priest of the Undying Sun_

**Requirement**  
Decisive contribution to the project or its direction 

<br>

<small><i>
Those whose actions shape the path of others and ensure the light endures.
</i></small>

</td>
</tr>
</table>

### Donors — The Path of the Temple Offering *(available after the first release)*

The Path of the Temple offering represents the material commitment to the project.
It is the path of those who wish to sustain and amplify its development.
Those who walk this this path will support :
- the purchase and maintenance of specific infrastructure
- compensation for those on the path of the serpent, depending on their rank and activity 
- production of merch.

<small><i><b>Historical note:</b> the Aztecs did not use metallic currency—value was expressed through goods, service, and offerings, a principle that inspires this path.</i></small>


<table>
<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/o1_tonalli_seed.png" width="140">
</td>
<td>

<h4>Tonalli Seed</h4>

<small><i>
Those who spark the first motion, bringing initial energy into the system.
</i></small>

</td>
</tr>

<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/o2_tlaxtli_contributor.png" width="140">
</td>
<td>

<h4>Tlaxtli Contributor</h4>


<small><i>
Those who give and sustain, turning intent into tangible support.
</i></small>

</td>
</tr>

<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/o3_Tlatquitl_backer.png" width="140">
</td>
<td>

<h4>Tlatquitl Backer</h4>


<small><i>
Those who provide the substance that allows ideas to take form and endure.
</i></small>

</td>
</tr>

<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/o4_Tonalli_flowkeeper.png" width="140">
</td>
<td>

<h4>Tonalli Flowkeeper</h4>

<small><i>
Those who maintain the flow, ensuring balance, continuity, and lasting momentum.
</i></small>

</td>
</tr>

<tr>
<td width="160" style="text-align:center; vertical-align:middle;">
<img src="/ometeotl/images/badges/o5_Teyola_source.png" width="140">
</td>
<td>

<h4>Teyolia Source</h4>


<small><i>
Those who stand at the origin, empowering the whole system through their presence.
</i></small>

</td>
</tr>
</table>