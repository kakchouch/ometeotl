---
title: "AuditEntry"
---

Source:
- [src/ometeotl_core/generic/authority.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generic/authority.py)

Local role:
Immutable audit row recording one command decision.

Big-picture role:
Traceability primitive for authoritative command boundaries enforced by [AuthorityCommandHandler](/ometeotl/documentation/class-reference/generic/authority-command-handler/).

Inheritance:
- frozen dataclass

Parameters and fields:
- `command_id: str`
- `actor_id: ObjectId`
- `command_type: str`
- `sequence: int`
- `accepted: bool`
- `reason: str`
- `validation_summary: JsonMap`
- `logged_at: str`

Methods:
- no custom methods

Example:

```python
# AuditEntry instances are produced by AuthorityCommandHandler and are read-only
handler = AuthorityCommandHandler(world=world)
handler.submit(envelope)

for entry in handler.audit_log:
    print(entry.command_id)
    print(entry.accepted)            # True | False
    print(entry.reason)              # human-readable decision reason
    print(entry.logged_at)           # ISO timestamp
    print(entry.validation_summary)  # staged validation metadata
```

See also:
- [CommandEnvelope](/ometeotl/documentation/class-reference/generic/command-envelope/)
- [CommandResult](/ometeotl/documentation/class-reference/generic/command-result/)
