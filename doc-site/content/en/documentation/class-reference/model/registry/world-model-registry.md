---
title: "WorldModelRegistry"
---

Source:
- [src/masm/model/registry.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/registry.py)

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
- mutation: `register`, `unregister`, `clear`
- lookup: `exists`, `get`, `all_ids`
- serialization: `to_dict`, `from_dict`
- guard wiring: `set_mutation_guard`

See also:
- [MinimalModelRegistry](/ometeotl/documentation/class-reference/model/registry/minimal-model-registry/)
