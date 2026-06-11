---
title: "Resource"
---

Source:
- [src/ometeotl_core/model/resources.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/resources.py)

Local role:
Represents modeled resources with rivalry and transferability semantics.

Big-picture role:
Constraint and capability component used by [Action](/ometeotl/documentation/class-reference/model/actions/action/) and related to [Actor](/ometeotl/documentation/class-reference/model/actors/actor/).

Inheritance:
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/)
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- `object_type: str = "resource"`
- resource attributes: `kind`, `resource_mode`, `rivalry`, `transferability`, `divisibility`, `composite`

Methods:
- attribute properties with setters for each resource attribute
- generated relation methods: `add_user/remove_user`, `add_owner/remove_owner`, `add_dependency/remove_dependency`, and related pairs
- `from_dict(...)`

Example:

```python
from ometeotl_core.model.resources import Resource

resource = Resource(id="fuel-1", kind="fuel")
resource.rivalry = "rival"
resource.transferability = "transferable"
resource.divisibility = "divisible"
resource.add_owner("actor-1")
resource.set_attribute("label", "Fuel Tank A")

data = resource.to_dict()
```

See also:
- [ResourceEffect](/ometeotl/documentation/class-reference/model/actions/resource-effect/)
