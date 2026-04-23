---
title: "Class Reference"
description: "One class per page reference for Ometeotl/MASM"
---

This section contains one page per implemented class.
The filetree mirrors the repository architecture in `src/masm/core`, `src/masm/model`, `src/masm/game`, and `src/masm/validation`.

Repository source:
- [GitHub repository](https://github.com/kakchouch/ometeotl)
- [specs_EN.md](https://github.com/kakchouch/ometeotl/blob/main/specs_EN.md)

## Core
- [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)
- [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
- [AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/)
- [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/)
- [RuntimeContext](/ometeotl/documentation/class-reference/core/runtime-context/)

## Validation
- [Validation index](/ometeotl/documentation/class-reference/validation/)
- [ValidationIssue](/ometeotl/documentation/class-reference/validation/validation-issue/)
- [ValidationContext](/ometeotl/documentation/class-reference/validation/validation-context/)
- [ValidationResult](/ometeotl/documentation/class-reference/validation/validation-result/)
- [ValidationPipeline](/ometeotl/documentation/class-reference/validation/validation-pipeline/)
- [Validation policy profiles](/ometeotl/documentation/class-reference/validation/validation-policy/)
- [DiagnosticBuilder](/ometeotl/documentation/class-reference/validation/diagnostic-builder/)
- [Validators overview](/ometeotl/documentation/class-reference/validation/validators-overview/)

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

## Model/projection.py
- [ProjectionAssumption](/ometeotl/documentation/class-reference/model/projection/projection-assumption/)
- [ProjectedPerceptionChange](/ometeotl/documentation/class-reference/model/projection/projected-perception-change/)
- [ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)
- [ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/)
- [ProjectionBatch](/ometeotl/documentation/class-reference/model/projection/projection-batch/)
- [ProjectionTool](/ometeotl/documentation/class-reference/model/projection/projection-tool/)
- [DefaultProjectionTool](/ometeotl/documentation/class-reference/model/projection/default-projection-tool/)

## Model/strategies.py
- [StrategyBuildStep](/ometeotl/documentation/class-reference/model/strategies/strategy-build-step/)
- [StrategyOutcomeBranch](/ometeotl/documentation/class-reference/model/strategies/strategy-outcome-branch/)
- [StrategyNode](/ometeotl/documentation/class-reference/model/strategies/strategy-node/)
- [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/)

## Model/goals.py
- [GoalBuildStep](/ometeotl/documentation/class-reference/model/goals/goal-build-step/)
- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/)
- [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/)

## Model/goal_tools.py
- [GoalFeasibilityResult](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-result/)
- [GoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/goal-feasibility-tool/)
- [DefaultGoalFeasibilityTool](/ometeotl/documentation/class-reference/model/goal-tools/default-goal-feasibility-tool/)
- [GoalAdmissibilityResult](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-result/)
- [GoalAdmissibilityChecker](/ometeotl/documentation/class-reference/model/goal-tools/goal-admissibility-checker/)

## Model/utility.py
- [UtilityFrame](/ometeotl/documentation/class-reference/model/utility/utility-frame/)
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/)

## Model/registry.py
- [reconstruct_model_object](/ometeotl/documentation/class-reference/model/registry/reconstruct-model-object/)
- [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/)
- [MinimalModelRegistry](/ometeotl/documentation/class-reference/model/registry/minimal-model-registry/)

## Model/world.py
- [World](/ometeotl/documentation/class-reference/model/world/world/)

## Game/utility.py
- [WeightedSumUtility](/ometeotl/documentation/class-reference/game/utility/weighted-sum-utility/)
- [LexicographicUtility](/ometeotl/documentation/class-reference/game/utility/lexicographic-utility/)
- [RankedStrategy](/ometeotl/documentation/class-reference/game/utility/ranked-strategy/)
- [StrategyRanker](/ometeotl/documentation/class-reference/game/utility/strategy-ranker/)

## IO
- [IO index](/ometeotl/documentation/class-reference/io/)
- [World export](/ometeotl/documentation/class-reference/io/world-export/)
- [World import / WorldImportResult](/ometeotl/documentation/class-reference/io/world-import/)
