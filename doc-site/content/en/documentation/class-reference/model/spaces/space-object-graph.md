---
title: "SpaceObjectGraph"
---

Source:
- [src/masm/model/spaces.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/spaces.py)

Local role:
Graph holding spaces and object memberships.

Big-picture role:
Deterministic topology service used by [World](/ometeotl/documentation/class-reference/model/world/world/) and [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/).

Inheritance:
- dataclass

Parameters and fields:
- spaces: Dict[ObjectId, [Space](/ometeotl/documentation/class-reference/model/spaces/space/)]
- object_memberships: List[[SpaceObjectMembership](/ometeotl/documentation/class-reference/model/spaces/space-object-membership/)]
- `_membership_keys: set[...]`

Methods:
- mutation: `add_space`, `add_object_membership`, `remove_object_membership`
- queries: `get_space`, `spaces_where_object_exists`, `shared_spaces_ids_for_objects`, `list_objects_in_space`
- serialization: `to_dict`, `from_dict`

See also:
- [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
