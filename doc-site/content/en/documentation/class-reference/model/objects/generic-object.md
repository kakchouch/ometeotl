---
title: "GenericObject"
---

Source:
- [src/masm/model/objects.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/objects.py)

Local role:
First semantic layer above [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/).

Big-picture role:
Shared convenience API inherited by [Actor](/ometeotl/documentation/class-reference/model/actors/actor/), [Resource](/ometeotl/documentation/class-reference/model/resources/resource/), and [Space](/ometeotl/documentation/class-reference/model/spaces/space/).

Inheritance:
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- inherited base fields

Methods:
- metadata properties: `label`, `description`, `tags`, `profile`
- metadata mutators: `add_tag`, `remove_tag`, `set_profile_item`
- space binding helpers: `add_space_membership`, `remove_space_membership` via [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/)

See also:
- [SpaceObjectMembership](/ometeotl/documentation/class-reference/model/spaces/space-object-membership/)
