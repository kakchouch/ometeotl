---
title: "WorldModelRegistry"
---

Source:
- [src/ometeotl_core/model/registry.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/registry.py)

Local role:
World-scoped in-memory registry of [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/) instances.

Big-picture role:
Identity boundary used by [World](/ometeotl/documentation/class-reference/model/world/world/) and by [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/).

Inheritance:
- standard class

Parameters and fields:
- internal `_instances` dictionary
- optional mutation guard callback

Methods:
- mutation: `register(obj, authority_token=None)`, `unregister(obj_id, authority_token=None)`, `clear(authority_token=None)`
- lookup: `exists(obj_id) -> bool`, `get(obj_id) -> Optional[ModelObject]`, `all_ids() -> list[ObjectId]`
- serialization: `to_dict() -> JsonMap`, `from_dict(data) -> WorldModelRegistry`
- guard wiring: `set_mutation_guard(guard)`

Notes:
- `authority_token` is forwarded to the mutation guard callback when set.
  Re-registering the exact same object instance is a no-op.
  Duplicate IDs from different object instances raise `ValueError`.

See also:
- [MinimalModelRegistry](/ometeotl/documentation/class-reference/model/registry/minimal-model-registry/)
