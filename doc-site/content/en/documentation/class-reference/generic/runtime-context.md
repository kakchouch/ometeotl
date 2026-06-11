---
title: "RuntimeContext"
---

Source:
- [src/ometeotl_core/generic/runtime.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generic/runtime.py)

Local role:
Context manager that bundles one [World](/ometeotl/documentation/class-reference/model/world/world/) with optional [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/).

Big-picture role:
Runtime switch between local mode and server-authoritative mode.

Inheritance:
- dataclass

Parameters and fields:
- world: [World](/ometeotl/documentation/class-reference/model/world/world/)
- authority_handler: Optional[[AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/)]

Methods:
- __enter__() -> [RuntimeContext](/ometeotl/documentation/class-reference/core/runtime-context/)
- `__exit__(...) -> None`
- `authoritative -> bool`
- `close() -> None`

Related function:
- `build_runtime(...)` in [src/ometeotl_core/generic/runtime.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generic/runtime.py)

Runtime policy options passed through `build_runtime(...)`:
- `validation_soft_gate`
- `validation_policy_profile` (`observe_only`, `enforce_structure`, `enforce_domain`)
- `validation_stage_mode_overrides`
- `validation_block_on_error`
- `validation_completeness_level`

Example:

```python
from ometeotl_core.generic.runtime import build_runtime

# Local mode: direct mutations allowed
with build_runtime(world=world) as ctx:
    print(ctx.authoritative)   # False — no AuthorityCommandHandler attached
    world.add_space(space)

# Authoritative mode: all mutations go through the handler
with build_runtime(
    world=world,
    validation_policy_profile="enforce_structure",
    validation_soft_gate=True,
) as ctx:
    result = ctx.authority_handler.submit(envelope)
    print(result.accepted)
```

See also:
- [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)
