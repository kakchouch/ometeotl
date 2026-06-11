---
title: "MinimalModelRegistry"
---

Source:
- [src/ometeotl_core/model/registry.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/registry.py)

Local role:
Global class-level fallback registry.

Big-picture role:
Legacy/simple referential integrity utility, while [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/) is preferred for world-scoped isolation.

Inheritance:
- standard class with class methods

Parameters and fields:
- class field `_instances: Dict[ObjectId, [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)]`

Methods:
- `register`, `unregister`, `exists`, `get`, `clear`, `all_ids`

Example:

```python
from ometeotl_core.model.registry import MinimalModelRegistry

# Class-level global registry — shared across all calls in the process
MinimalModelRegistry.register(actor)
assert MinimalModelRegistry.exists("actor-1")

obj = MinimalModelRegistry.get("actor-1")
MinimalModelRegistry.unregister("actor-1")

# Prefer WorldModelRegistry for world-scoped isolation in production code
```

See also:
- [World](/ometeotl/documentation/class-reference/model/world/world/)
