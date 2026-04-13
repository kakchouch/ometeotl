---
title: "SpaceRelation"
---

Source:
- [src/masm/model/space_relations.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/space_relations.py)

Local role:
Typed edge linking two spaces.

Big-picture role:
Space topology primitive used by [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/) and copied into [PerceivedRelation](/ometeotl/documentation/class-reference/model/perception/perceived-relation/).

Inheritance:
- frozen dataclass

Parameters and fields:
- `source_space_id: SpaceId`
- `target_space_id: SpaceId`
- `relation_type: str`
- `metadata: JsonMap`

Methods:
- `canonicalize(...)`
- `to_dict(...)`
- `from_dict(...)`
- `__deepcopy__(...)`

See also:
- [SpaceRelationType](/ometeotl/documentation/class-reference/model/space-relations/space-relation-type/)
