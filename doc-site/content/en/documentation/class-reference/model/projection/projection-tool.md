---
title: "ProjectionTool"
---

Source:
- [src/masm/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/projection.py)

Local role:
Abstract contract for deriving assumption sets from [Action](/ometeotl/documentation/class-reference/model/actions/action/), [Perception](/ometeotl/documentation/class-reference/model/perception/perception/), and [Resource](/ometeotl/documentation/class-reference/model/resources/resource/) inputs.

Big-picture role:
Extensibility seam for projection logic that stays separate from strategy-node construction.

Inheritance:
- abstract base class

Methods:
- `project_action(action, perception, resources=()) -> ActionProjection`
- `project_actions(actions, perception, resources=()) -> ProjectionBatch`

See also:
- [ScaffoldProjectionTool](/ometeotl/documentation/class-reference/model/projection/scaffold-projection-tool/)