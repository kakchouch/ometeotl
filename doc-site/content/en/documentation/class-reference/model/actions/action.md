---
title: "Action"
---

Source:
- [src/masm/model/actions.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/actions.py)

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

See also:
- [Resource](/ometeotl/documentation/class-reference/model/resources/resource/)
