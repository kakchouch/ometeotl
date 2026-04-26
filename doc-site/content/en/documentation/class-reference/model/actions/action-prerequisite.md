---
title: "ActionPrerequisite"
---

Source:
- [src/ometeotl_core/model/actions.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/actions.py)

Local role:
One admissibility condition attached to one [Action](/ometeotl/documentation/class-reference/model/actions/action/).

Big-picture role:
Models constraints based on resources, capabilities, perception, or space rules linked to [Actor](/ometeotl/documentation/class-reference/model/actors/actor/).

Inheritance:
- dataclass

Parameters and fields:
- `prerequisite_type: str`
- `field_name: str`
- `required_value: Any`
- `metadata: JsonMap`

Methods:
- `to_dict(...)`
- `from_dict(...)`

See also:
- [ResourceEffect](/ometeotl/documentation/class-reference/model/actions/resource-effect/)
