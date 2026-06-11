---
title: "PerceivedComponentLink"
---

Source:
- [src/ometeotl_core/model/perception.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/perception.py)

Local role:
Epistemic wrapper for one perceived composition edge between a composite actor and one component actor.

Big-picture role:
Lets [Perception](/ometeotl/documentation/class-reference/model/perception/perception/) represent actor hierarchy knowledge without mutating the ontological [Actor](/ometeotl/documentation/class-reference/model/actors/actor/) graph.

Inheritance:
- dataclass

Parameters and fields:
- `link_id: str`
- `composite_id: ObjectId`
- `component_id: ObjectId`
- `epistemic_status: str`
- `noise_metadata: JsonMap`

Methods:
- `to_dict(...)`
- `from_dict(...)`
- `__post_init__(...)`

Notes:
- `epistemic_status` follows the same validation rules as the other perceived wrappers.
- This type is used both for sensed hierarchy knowledge and for projected hierarchy updates in successor perceived states.

Example:

```python
from ometeotl_core.model.perception import PerceivedComponentLink

link = PerceivedComponentLink(
    link_id="link-1",
    composite_id="team-1",
    component_id="actor-1",
    epistemic_status="believed",
    noise_metadata={},
)
data = link.to_dict()

# Query from a Perception object
links = perception.component_links_for_composite("team-1")
parent = perception.composite_for_component("actor-1")
```

See also:
- [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)
- [Actor](/ometeotl/documentation/class-reference/model/actors/actor/)
- [ProjectedPerceptionChange](/ometeotl/documentation/class-reference/model/projection/projected-perception-change/)
