---
title: "Perception"
---

Source:
- [src/masm/model/perception.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/perception.py)

Local role:
Subject-specific partial world snapshot.

Big-picture role:
Formal epistemic layer that separates what the world is from what an actor knows through [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/).

Inheritance:
- dataclass

Parameters and fields:
- `id: str`
- `actor_id: ObjectId`
- `source_id: ObjectId`
- `schema_version: str`
- `timestamp: Optional[Union[int, float, str]]`
- perceived_spaces: Dict[SpaceId, [PerceivedSpace](/ometeotl/documentation/class-reference/model/perception/perceived-space/)]
- perceived_memberships: List[[PerceivedMembership](/ometeotl/documentation/class-reference/model/perception/perceived-membership/)]
- perceived_relations: List[[PerceivedRelation](/ometeotl/documentation/class-reference/model/perception/perceived-relation/)]
- `context: JsonMap`
- `provenance: JsonMap`

Methods:
- query helpers: `get_perceived_space`, `memberships_for_object`, `memberships_in_space`, `relations_for_space`
- serialization: `to_dict`, `from_dict`

See also:
- [Actor](/ometeotl/documentation/class-reference/model/actors/actor/)
- [World](/ometeotl/documentation/class-reference/model/world/world/)
