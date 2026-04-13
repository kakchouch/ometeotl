---
title: "Overview"
description: "Three-level walkthrough of how Ometeotl/MASM works internally"
---

This page explains the internal workings of Ometeotl/MASM at three depth levels.

For API-level details, use [Class Reference](/ometeotl/documentation/class-reference/).

## Beginner View

Ometeotl/MASM is a modeling library where everything starts from a generic object, then becomes more specific.

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
8. Optionally enforce command gating with [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/).

Operationally, [World](/ometeotl/documentation/class-reference/model/world/world/) composes three independent graphs/registries:

- membership topology: [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/)
- spatial topology: [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
- object identity and lookup: [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/)

This separation prevents layer mixing and aligns with the architecture constraints in [specs_EN.md](https://github.com/kakchouch/ometeotl/blob/main/specs_EN.md).

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

### 4. Extensibility seam

Primary extension seams are intentionally abstract and composable:

- [CoverageRule](/ometeotl/documentation/class-reference/model/sensor/coverage-rule/) and [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/) for sensing behavior
- custom object reconstruction factories through registry helpers and authority handlers
- custom command handlers injected into [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/)

### 5. Runtime wiring

[RuntimeContext](/ometeotl/documentation/class-reference/core/runtime-context/) plus `build_runtime(...)` provide explicit mode selection:

- local mode: direct world mutation APIs
- server-authoritative mode: command-gated mutation via [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/)

This keeps local testing ergonomics while preserving an enforceable server boundary for multi-client systems.
