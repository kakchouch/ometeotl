---
title: "SpaceObjectMembership"
---

Source:
- [src/ometeotl_core/model/spaces.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/spaces.py)

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

Example:

```python
from ometeotl_core.model.spaces import SpaceObjectMembership

membership = SpaceObjectMembership(
    object_id="actor-1",
    space_id="zone-1",
    role="occupies",
    validity={"from": 0},
    metadata={"confirmed": True},
)
data = membership.to_dict()
m2 = SpaceObjectMembership.from_dict(data)

# Typically added through World.place_object or SpaceObjectGraph.add_object_membership
```

See also:
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
