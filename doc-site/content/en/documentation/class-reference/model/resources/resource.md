---
title: "Resource"
---

Source:
- [src/masm/model/resources.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/resources.py)

Local role:
Represents modeled resources with rivalry and transferability semantics.

Big-picture role:
Constraint and capability component used by [Action](/ometeotl/documentation/class-reference/model/actions/action/) and related to [Actor](/ometeotl/documentation/class-reference/model/actors/actor/).

Inheritance:
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/)
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- `object_type: str = "resource"`
- resource attributes: `kind`, `resource_mode`, `rivalry`, `transferability`, `divisibility`, `composite`

Methods:
- attribute properties with setters for each resource attribute
- generated relation methods: `add_user/remove_user`, `add_owner/remove_owner`, `add_dependency/remove_dependency`, and related pairs
- `from_dict(...)`

See also:
- [ResourceEffect](/ometeotl/documentation/class-reference/model/actions/resource-effect/)
