---
title: "Actor"
---

Source:
- [src/masm/model/actors.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/actors.py)

Local role:
Represents an actor entity with roles, composition mode, and domain relations.

Big-picture role:
Central decision-capable abstraction consumed by [Action](/ometeotl/documentation/class-reference/model/actions/action/) and observed through [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/).

Inheritance:
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/)
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- `object_type: str = "actor"`
- actor attributes: `kind`, `roles`, `emergent`, `composition_mode`

Methods:
- actor properties: `kind`, `roles`, `emergent`, `composition_mode`
- role methods: `add_role`, `remove_role`
- generated relation methods: `add_action/remove_action`, `add_resource/remove_resource`, `add_goal/remove_goal`, and related pairs
- `from_dict(...)`

See also:
- [Resource](/ometeotl/documentation/class-reference/model/resources/resource/)
- [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)
