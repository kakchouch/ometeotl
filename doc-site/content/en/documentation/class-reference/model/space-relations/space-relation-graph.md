---
title: "SpaceRelationGraph"
---

Source:
- [src/masm/model/space_relations.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/space_relations.py)

Local role:
Validated relation graph over spaces.

Big-picture role:
Topology query and validation layer used by [World](/ometeotl/documentation/class-reference/model/world/world/) and by [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/) through [Perception](/ometeotl/documentation/class-reference/model/perception/perception/).

Inheritance:
- dataclass

Parameters and fields:
- relations: List[[SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/)]
- `_relation_keys: set[...]`

Methods:
- mutation: `add_relation`, `remove_relation`
- queries: `relations_from`, `relations_to`, `children_of`, `parents_of`, `neighbors_of`, `intersects_with`
- serialization: `to_dict`, `from_dict`

See also:
- [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/)
