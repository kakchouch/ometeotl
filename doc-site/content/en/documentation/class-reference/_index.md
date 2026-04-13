---
title: "Class Reference"
description: "One class per page reference for Ometeotl/MASM"
---

This section contains one page per implemented class.
The filetree mirrors the repository architecture in `src/masm/core` and `src/masm/model`.

Repository source:
- [GitHub repository](https://github.com/kakchouch/ometeotl)
- [specs_EN.md](https://github.com/kakchouch/ometeotl/blob/main/specs_EN.md)

## Core
- [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)
- [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
- [AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/)
- [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/)
- [RuntimeContext](/ometeotl/documentation/class-reference/core/runtime-context/)

## Model/base.py
- [GuardedJsonDict](/ometeotl/documentation/class-reference/model/base/guarded-json-dict/)
- [GuardedJsonList](/ometeotl/documentation/class-reference/model/base/guarded-json-list/)
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

## Model/objects.py
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/)

## Model/actors.py
- [Actor](/ometeotl/documentation/class-reference/model/actors/actor/)

## Model/resources.py
- [Resource](/ometeotl/documentation/class-reference/model/resources/resource/)

## Model/spaces.py
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
- [SpaceObjectMembership](/ometeotl/documentation/class-reference/model/spaces/space-object-membership/)
- [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/)

## Model/space_relations.py
- [SpaceRelationType](/ometeotl/documentation/class-reference/model/space-relations/space-relation-type/)
- [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/)
- [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)

## Model/perception.py
- [PerceivedSpace](/ometeotl/documentation/class-reference/model/perception/perceived-space/)
- [PerceivedMembership](/ometeotl/documentation/class-reference/model/perception/perceived-membership/)
- [PerceivedRelation](/ometeotl/documentation/class-reference/model/perception/perceived-relation/)
- [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)

## Model/sensor.py
- [CoverageRule](/ometeotl/documentation/class-reference/model/sensor/coverage-rule/)
- [TotalCoverageRule](/ometeotl/documentation/class-reference/model/sensor/total-coverage-rule/)
- [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/)
- [IdentityNoiseRule](/ometeotl/documentation/class-reference/model/sensor/identity-noise-rule/)
- [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/)

## Model/actions.py
- [Action](/ometeotl/documentation/class-reference/model/actions/action/)
- [ResourceEffect](/ometeotl/documentation/class-reference/model/actions/resource-effect/)
- [ActionPrerequisite](/ometeotl/documentation/class-reference/model/actions/action-prerequisite/)

## Model/registry.py
- [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/)
- [MinimalModelRegistry](/ometeotl/documentation/class-reference/model/registry/minimal-model-registry/)

## Model/world.py
- [World](/ometeotl/documentation/class-reference/model/world/world/)
