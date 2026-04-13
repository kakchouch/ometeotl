---
title: "AuditEntry"
---

Source:
- [src/masm/core/authority.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/core/authority.py)

Local role:
Immutable audit row recording one command decision.

Big-picture role:
Traceability primitive for authoritative command boundaries enforced by [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/).

Inheritance:
- frozen dataclass

Parameters and fields:
- `command_id: str`
- `actor_id: ObjectId`
- `command_type: str`
- `sequence: int`
- `accepted: bool`
- `reason: str`
- `logged_at: str`

Methods:
- no custom methods

See also:
- [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)
- [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
