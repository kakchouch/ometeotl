---
title: "SpaceRelationType"
---

Source:
- [src/ometeotl_core/model/space_relations.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/space_relations.py)

Local role:
Metadata definition for one relation type.

Big-picture role:
Rule descriptor consumed by [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/) and [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/).

Inheritance:
- frozen dataclass

Parameters and fields:
- `name: str`
- `is_symmetric: bool`
- `is_antisymmetric: bool`
- `is_transitive: bool`
- `is_reflexive: bool`

Methods:
- no custom methods

Example:

```python
from ometeotl_core.model.space_relations import SpaceRelationType

# Symmetric undirected relation (e.g. two adjacent zones)
adjacent = SpaceRelationType(
    name="adjacent",
    is_symmetric=True,
    is_antisymmetric=False,
    is_transitive=False,
    is_reflexive=False,
)

# Antisymmetric transitive containment relation
contains = SpaceRelationType(
    name="contains",
    is_symmetric=False,
    is_antisymmetric=True,
    is_transitive=True,
    is_reflexive=False,
)
```

See also:
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
