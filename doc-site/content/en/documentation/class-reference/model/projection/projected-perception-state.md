---
title: "ProjectedPerceptionState"
---

Source:
- [src/ometeotl_core/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/projection.py)

Local role:
Projected successor perceived state produced by evaluating one [Action](/ometeotl/documentation/class-reference/model/actions/action/) from one source [Perception](/ometeotl/documentation/class-reference/model/perception/perception/).

Big-picture role:
Bridge object between first-order projection and later strategy construction: it is the state that child strategy nodes consume.

Inheritance:
- dataclass

Parameters and fields:
- `source_perception_id: str`
- `generating_action_id: str`
- `perception: Perception` — deep copy of the source perception, marked `epistemic_status="projected"` on perceived spaces, memberships, relations, and perceived component links
- `changes: list[ProjectedPerceptionChange]` — sorted by `change_id` on serialization
- `metadata: dict`

Context keys written into `perception.context`:
- `projected_state_changes` — map of action-id to state-change payloads from `action.state_changes`
- `projected_stock_deltas` — map of `resource_id` to cumulative quantity delta for stock resources (mode `"stock"` with `quantity != 1.0`); consume subtracts, produce adds, transfer subtracts from source

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> ProjectedPerceptionState`

Example:

```python
tool = DefaultProjectionTool()
proj = tool.project_action(action, perception, resources=[resource])

if proj.projected_state:
    pps = proj.projected_state
    successor_perception = pps.perception   # deep-copied, epistemic_status="projected"

    for change in pps.changes:
        print(change.change_type, change.subject_id, change.applied)

    # Stock resource deltas written into context
    deltas = pps.perception.context.get("projected_stock_deltas", {})
```

See also:
- [ProjectedPerceptionChange](/ometeotl/documentation/class-reference/model/projection/projected-perception-change/)
- [ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/)
- [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)