---
title: "RuntimeContext"
---

Source:
- [src/masm/core/runtime.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/core/runtime.py)

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
- `build_runtime(...)` in [src/masm/core/runtime.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/core/runtime.py)

See also:
- [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)
