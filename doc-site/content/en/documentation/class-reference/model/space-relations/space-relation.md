---
title: "SpaceRelation"
---

Source:
- [src/ometeotl_core/model/space_relations.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/space_relations.py)

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

Example:

```python
from ometeotl_core.model.space_relations import SpaceRelation

# Directed relation: zone-1 is adjacent to zone-2
relation = SpaceRelation(
    source_space_id="zone-1",
    target_space_id="zone-2",
    relation_type="adjacent",
    metadata={"distance": 10},
)
# Canonicalize sorts source/target for symmetric relations
canonical = relation.canonicalize(is_symmetric=True)
data = relation.to_dict()
r2 = SpaceRelation.from_dict(data)
```

See also:
- [SpaceRelationType](/ometeotl/documentation/class-reference/model/space-relations/space-relation-type/)
