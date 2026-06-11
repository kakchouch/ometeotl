---
title: "PerceivedRelation"
---

Source:
- [src/ometeotl_core/model/perception.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/perception.py)

Local role:
Epistemic wrapper around one copied [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/).

Big-picture role:
Actor-relative space-topology knowledge element in [Perception](/ometeotl/documentation/class-reference/model/perception/perception/).

Inheritance:
- dataclass

Parameters and fields:
- relation: [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/)
- `epistemic_status: str`
- `noise_metadata: JsonMap`

Methods:
- `to_dict(...)`
- `from_dict(...)`
- `__post_init__(...)`

Example:

```python
from ometeotl_core.model.perception import PerceivedRelation

pr = PerceivedRelation(
    relation=relation,
    epistemic_status="hypothesis",
    noise_metadata={},
)
print(pr.relation.relation_type)   # e.g. "adjacent"
print(pr.epistemic_status)         # "hypothesis"

data = pr.to_dict()
```

See also:
- [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
