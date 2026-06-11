---
title: "GuardedJsonList"
---

Source:
- [src/ometeotl_core/model/base.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/base.py)

Local role:
Guarded list wrapper used in mutable fields of [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/).

Big-picture role:
Extends authority-safe mutation behavior to list operations in objects managed by [World](/ometeotl/documentation/class-reference/model/world/world/).

Inheritance:
- `list[Any]`

Parameters and fields:
- `initial: List[Any] | None`
- `mutation_guard: MutationGuard`

Methods:
- `set_mutation_guard(...)`
- guarded mutators: `append`, `extend`, `insert`, `pop`, `remove`, `reverse`, `sort`, `__setitem__`, `__delitem__`, `__iadd__`
- `__deepcopy__(...)`

Example:

```python
from ometeotl_core.model.base import GuardedJsonList

lst = GuardedJsonList(["tag-a", "tag-b"])
lst.append("tag-c")        # allowed — no guard active
lst.remove("tag-a")

# When a World enables authority mode, the mutation guard fires
# and lst.append(value) raises RuntimeError until authority mode is disabled.
```

See also:
- [GuardedJsonDict](/ometeotl/documentation/class-reference/model/base/guarded-json-dict/)
