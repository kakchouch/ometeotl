---
title: "Action"
---

Source:
- [src/ometeotl_core/model/actions.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/actions.py)

Local role:
Represents one actor-driven state transition in one world and one space.

Big-picture role:
Operational unit tying [Actor](/ometeotl/documentation/class-reference/model/actors/actor/), [World](/ometeotl/documentation/class-reference/model/world/world/), [ResourceEffect](/ometeotl/documentation/class-reference/model/actions/resource-effect/), and [ActionPrerequisite](/ometeotl/documentation/class-reference/model/actions/action-prerequisite/).

Inheritance:
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- `object_type: str = "action"`
- `actor_id: ObjectId`
- `world_id: ObjectId`
- `space_id: ObjectId`
- `action_type: str`
- resource_effects: List[[ResourceEffect](/ometeotl/documentation/class-reference/model/actions/resource-effect/)]
- prerequisites: List[[ActionPrerequisite](/ometeotl/documentation/class-reference/model/actions/action-prerequisite/)]
- `outcome_description: str`
- `state_changes: JsonMap`

Methods:
- `add_resource_effect(...)`
- `add_prerequisite(...)`
- `set_state_change(...)`
- `to_dict(...)`, `from_dict(...)`

Example:

```python
from ometeotl_core.model.actions import Action, ResourceEffect, ActionPrerequisite

action = Action(
    id="action-1",
    actor_id="actor-1",
    world_id="world-1",
    space_id="zone-1",
    action_type="move",
    outcome_description="Actor moves to target space",
)
action.add_resource_effect(ResourceEffect(
    resource_id="fuel-1", effect_type="consume", quantity=1.0
))
action.add_prerequisite(ActionPrerequisite(
    prerequisite_type="capability", field_name="mobility", required_value=True
))
action.set_state_change("location", "zone-2")

data = action.to_dict()
```

See also:
- [Resource](/ometeotl/documentation/class-reference/model/resources/resource/)
