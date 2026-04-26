---
title: "Space"
---

Source:
- [src/ometeotl_core/model/spaces.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/spaces.py)

Local role:
Represents one space of existence.

Big-picture role:
Fundamental topological unit used by [World](/ometeotl/documentation/class-reference/model/world/world/), [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/), [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/), and [PerceivedSpace](/ometeotl/documentation/class-reference/model/perception/perceived-space/).

Inheritance:
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/)
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- `object_type: str = "space"`
- space attributes: `kind`, `dimensions`, `validity`, `is_abstract`

Methods:
- space properties: `kind`, `dimensions`, `validity`, `is_abstract`
- dimension and validity methods: `set_dimension`, `set_validity`
- legacy disabled methods: `add_member`, `remove_member`, `connect_to`
- `from_dict(...)`, `__deepcopy__(...)`

Notes:
- `is_abstract` marks non-canonical spaces such as conceptual, analytical, or strategic grouping spaces.
- Abstract spaces support the multi-space model described in the spec and can host abstraction-layer actors without changing the canonical world object model.

See also:
- [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/)
- [SpaceObjectMembership](/ometeotl/documentation/class-reference/model/spaces/space-object-membership/)
- [World](/ometeotl/documentation/class-reference/model/world/world/)
