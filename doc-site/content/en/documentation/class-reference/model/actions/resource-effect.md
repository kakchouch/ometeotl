---
title: "ResourceEffect"
---

Source:
- [src/masm/model/actions.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/actions.py)

Local role:
Describes one resource effect of one [Action](/ometeotl/documentation/class-reference/model/actions/action/).

Big-picture role:
Encodes consumption, production, or transfer semantics for [Resource](/ometeotl/documentation/class-reference/model/resources/resource/).

Inheritance:
- dataclass

Parameters and fields:
- `resource_id: ObjectId`
- `effect_type: str`
- `quantity: float`
- `source_id: Optional[ObjectId]`
- `target_id: Optional[ObjectId]`
- `metadata: JsonMap`

Methods:
- `to_dict(...)`
- `from_dict(...)`

See also:
- [ActionPrerequisite](/ometeotl/documentation/class-reference/model/actions/action-prerequisite/)
