---
title: "Space"
---

Source:
- [src/masm/model/spaces.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/spaces.py)

Local role:
Represents one space of existence.

Big-picture role:
Fundamental topological unit used by [World](/ometeotl/documentation/class-reference/model/world/world/), [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/), [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/), and [PerceivedSpace](/ometeotl/documentation/class-reference/model/perception/perceived-space/).

Inheritance:
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/)
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- `object_type: str = "space"`
- space attributes: `kind`, `dimensions`, `validity`

Methods:
- dimension and validity methods: `set_dimension`, `set_validity`
- legacy disabled methods: `add_member`, `remove_member`, `connect_to`
- `from_dict(...)`, `__deepcopy__(...)`

See also:
- [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/)
- [SpaceObjectMembership](/ometeotl/documentation/class-reference/model/spaces/space-object-membership/)
