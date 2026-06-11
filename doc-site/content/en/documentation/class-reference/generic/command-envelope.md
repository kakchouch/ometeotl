---
title: "CommandEnvelope"
---

Source:
- [src/ometeotl_core/generic/authority.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generic/authority.py)

Local role:
Canonical command payload consumed by [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/).

Big-picture role:
Transport object that standardizes authoritative world mutation requests targeting [World](/ometeotl/documentation/class-reference/model/world/world/).

Inheritance:
- frozen dataclass

Parameters and fields:
- `command_id: str`
- `actor_id: ObjectId`
- `command_type: str`
- `payload: JsonMap`
- `sequence: int`
- `issued_at: str`

Methods:
- `to_dict() -> JsonMap`
- from_dict(data) -> [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)

Example:

```python
from ometeotl_core.generic.authority import CommandEnvelope
import datetime

envelope = CommandEnvelope(
    command_id="cmd-001",
    actor_id="actor-1",
    command_type="add_space",
    payload={"space": space.to_dict()},
    sequence=1,
    issued_at=datetime.datetime.utcnow().isoformat(),
)
data = envelope.to_dict()
envelope2 = CommandEnvelope.from_dict(data)
```

See also:
- [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
- [AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/)
