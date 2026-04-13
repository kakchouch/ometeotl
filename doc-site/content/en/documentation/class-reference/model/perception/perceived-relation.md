---
title: "PerceivedRelation"
---

Source:
- [src/masm/model/perception.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/perception.py)

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

See also:
- [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
