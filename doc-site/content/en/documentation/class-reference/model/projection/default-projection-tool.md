---
title: "DefaultProjectionTool"
---

Source:
- [src/ometeotl_core/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/projection.py)

Local role:
Minimal concrete [ProjectionTool](/ometeotl/documentation/class-reference/model/projection/projection-tool/) that turns action/perception/resource inputs into explicit assumptions and one projected successor perceived state without executing actions or building strategy nodes.

Big-picture role:
First-order strategizing helper: it prepares both the assumption basis and the next perceived state that later strategy-building steps may consume.

Inheritance:
- [ProjectionTool](/ometeotl/documentation/class-reference/model/projection/projection-tool/)

Methods:
- `project_action(action, perception, resources=()) -> ActionProjection`
  - Builds [ProjectionAssumption](/ometeotl/documentation/class-reference/model/projection/projection-assumption/) entries for actor binding, source context, space binding, each `ResourceEffect` (indexed as `effect:{idx}:…`), and each `ActionPrerequisite` (indexed as `prerequisite:{idx}:…`).
  - For `consume`/`transfer` effects, verifies that the resource has a `PerceivedMembership` in `effect.source_id` (or `action.space_id` as fallback); sets `satisfied=False` when the resource is not perceived there.
  - Calls `_build_projected_perception_state` and attaches the result as `projected_state`.
  - Status is `"projected"` when all required resources are satisfied and the actor matches; `"partial"` if resources or actor mismatch; `"blocked"` otherwise.
- inherited `project_actions(actions, perception, resources=()) -> ProjectionBatch`

Resource projection modes:
- **Discrete** (`resource_mode != "stock"` or `quantity == 1.0`): consume removes `PerceivedMembership`, produce appends one, transfer moves membership between spaces.
- **Stock** (`resource_mode == "stock"` and `quantity != 1.0`): writes a cumulative delta to `perception.context["projected_stock_deltas"]` instead of changing memberships.

Related module-level function:
- [`reconstruct_model_object`](/ometeotl/documentation/class-reference/model/registry/reconstruct-model-object/) in [src/ometeotl_core/model/registry.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/registry.py)

Example:

```python
from ometeotl_core.model.projection import DefaultProjectionTool

tool = DefaultProjectionTool()
projection = tool.project_action(action, perception, resources=[fuel_resource])

# Inspect assumption satisfaction
for assumption in projection.assumptions:
    print(assumption.assumption_type, "->", assumption.satisfied)

# Inspect the projected successor state
if projection.projected_state:
    for change in projection.projected_state.changes:
        print(change.change_type, change.subject_id)
```

See also:
- [ProjectionAssumption](/ometeotl/documentation/class-reference/model/projection/projection-assumption/)
- [ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/)
- [ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)