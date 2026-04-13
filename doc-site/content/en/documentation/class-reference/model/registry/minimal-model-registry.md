---
title: "MinimalModelRegistry"
---

Source:
- [src/masm/model/registry.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/registry.py)

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

See also:
- [World](/ometeotl/documentation/class-reference/model/world/world/)
