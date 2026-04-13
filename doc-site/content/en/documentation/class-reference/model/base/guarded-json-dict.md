---
title: "GuardedJsonDict"
---

Source:
- [src/masm/model/base.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/base.py)

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

See also:
- [GuardedJsonList](/ometeotl/documentation/class-reference/model/base/guarded-json-list/)
