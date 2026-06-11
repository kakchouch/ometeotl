---
title: "SpaceRelationGraph"
---

Source:
- [src/ometeotl_core/model/space_relations.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/space_relations.py)

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

Example:

```python
from ometeotl_core.model.space_relations import SpaceRelationGraph, SpaceRelation

graph = SpaceRelationGraph()
graph.add_relation(SpaceRelation(
    source_space_id="zone-1", target_space_id="zone-2", relation_type="adjacent"
))
graph.add_relation(SpaceRelation(
    source_space_id="zone-2", target_space_id="zone-3", relation_type="adjacent"
))

neighbors = graph.neighbors_of("zone-1")      # ["zone-2"]
children = graph.children_of("zone-1")        # directed children
data = graph.to_dict()
```

See also:
- [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/)
