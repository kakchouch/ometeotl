---
title: "Perception"
---

Source:
- [src/ometeotl_core/model/perception.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/perception.py)

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
- perceived_component_links: List[[PerceivedComponentLink](/ometeotl/documentation/class-reference/model/perception/perceived-component-link/)]
- `context: JsonMap`
- `provenance: JsonMap`

Methods:
- query helpers: `get_perceived_space`, `memberships_for_object`, `memberships_in_space`, `relations_for_space`, `component_links_for_composite`, `composite_for_component`
- serialization: `to_dict`, `from_dict`

Notes:
- A perception can now carry perceived composition edges independently from space memberships and space-to-space relations.
- Each perceived component link has its own epistemic status, allowing composition knowledge to remain uncertain, believed, projected, or erroneous without mutating ontological actor relations.

Example:

```python
from ometeotl_core.model.sensor import Sensor, TotalCoverageRule, IdentityNoiseRule

sensor = Sensor(
    coverage_rules=[TotalCoverageRule()],
    noise_rules=[IdentityNoiseRule()],
    default_epistemic_status="certain",
)
perception = sensor.sense(world, actor_id="actor-1", timestamp=0)

# Query helpers
pspace = perception.get_perceived_space("zone-1")
memberships = perception.memberships_for_object("actor-1")
in_zone = perception.memberships_in_space("zone-1")
topology = perception.relations_for_space("zone-1")

data = perception.to_dict()
```

See also:
- [Actor](/ometeotl/documentation/class-reference/model/actors/actor/)
- [World](/ometeotl/documentation/class-reference/model/world/world/)
- [PerceivedComponentLink](/ometeotl/documentation/class-reference/model/perception/perceived-component-link/)
