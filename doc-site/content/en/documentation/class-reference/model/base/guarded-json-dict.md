---
title: "GuardedJsonDict"
---

Source:
- [src/ometeotl_core/model/base.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/base.py)

Local role:
Guarded dictionary wrapper used in mutable fields of [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/).

Big-picture role:
Prevents direct mutations when authority lock is active through [World](/ometeotl/documentation/class-reference/model/world/world/).

Inheritance:
- `dict[str, Any]`

Parameters and fields:
- `initial: Mapping[str, Any] | None`
- `mutation_guard: MutationGuard`

Methods:
- `set_mutation_guard(...)`
- guarded mutators: `__setitem__`, `__delitem__`, `clear`, `pop`, `popitem`, `setdefault`, `update`
- `__deepcopy__(...)`

Example:

```python
from ometeotl_core.model.base import GuardedJsonDict

d = GuardedJsonDict({"status": "active"})
d["status"] = "inactive"   # allowed — no guard active
d["new_key"] = 42

# When a World enables authority mode, the mutation guard fires
# and d["key"] = value raises RuntimeError until authority mode is disabled.
```

See also:
- [GuardedJsonList](/ometeotl/documentation/class-reference/model/base/guarded-json-list/)
