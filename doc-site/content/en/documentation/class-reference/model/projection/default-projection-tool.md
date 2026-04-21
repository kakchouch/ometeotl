---
title: "DefaultProjectionTool"
---

Source:
- [src/masm/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/projection.py)

Local role:
Minimal concrete [ProjectionTool](/ometeotl/documentation/class-reference/model/projection/projection-tool/) that turns action/perception/resource inputs into explicit assumptions without executing actions or building strategy nodes.

Big-picture role:
First-order strategizing helper: it prepares the assumption basis that later strategy-building steps may consume.

Inheritance:
- [ProjectionTool](/ometeotl/documentation/class-reference/model/projection/projection-tool/)

Methods:
- `project_action(action, perception, resources=()) -> ActionProjection`
- inherited `project_actions(actions, perception, resources=()) -> ProjectionBatch`

Related function:
- `project_actions(...)` in [src/masm/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/projection.py)

See also:
- [ProjectionAssumption](/ometeotl/documentation/class-reference/model/projection/projection-assumption/)
- [ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/)