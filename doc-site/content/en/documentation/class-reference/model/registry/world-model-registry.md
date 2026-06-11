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

Example:

```python
from ometeotl_core.model.registry import WorldModelRegistry

registry = WorldModelRegistry()
registry.register(actor)
registry.register(resource)

assert registry.exists("actor-1")
obj = registry.get("actor-1")
all_ids = registry.all_ids()

# Serialize and restore the full registry
data = registry.to_dict()
registry2 = WorldModelRegistry.from_dict(data)
```

See also:
- [MinimalModelRegistry](/ometeotl/documentation/class-reference/model/registry/minimal-model-registry/)
