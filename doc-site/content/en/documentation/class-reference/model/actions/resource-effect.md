---
title: "ResourceEffect"
---

Source:
- [src/ometeotl_core/model/actions.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/actions.py)

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

Example:

```python
from ometeotl_core.model.actions import ResourceEffect

# Consume effect: actor uses 5 units of fuel from a depot space
effect = ResourceEffect(
    resource_id="fuel-1",
    effect_type="consume",
    quantity=5.0,
    source_id="depot-1",
)

# Transfer effect: move resource between two spaces
transfer = ResourceEffect(
    resource_id="fuel-1",
    effect_type="transfer",
    quantity=1.0,
    source_id="depot-1",
    target_id="vehicle-1",
)
data = effect.to_dict()
```

See also:
- [ActionPrerequisite](/ometeotl/documentation/class-reference/model/actions/action-prerequisite/)
