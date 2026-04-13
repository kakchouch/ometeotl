---
title: "SpaceObjectMembership"
---

Source:
- [src/masm/model/spaces.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/spaces.py)

Local role:
Canonical object-to-space membership record.

Big-picture role:
Placement primitive used by [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/), [World](/ometeotl/documentation/class-reference/model/world/world/), and perceived by [PerceivedMembership](/ometeotl/documentation/class-reference/model/perception/perceived-membership/).

Inheritance:
- dataclass

Parameters and fields:
- `object_id: ObjectId`
- `space_id: ObjectId`
- `role: str`
- `validity: JsonMap`
- `metadata: JsonMap`

Methods:
- `to_dict(...)`
- `from_dict(...)`
- `__deepcopy__(...)`

See also:
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
