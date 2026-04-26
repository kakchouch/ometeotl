---
title: "AuditEntry"
---

Source:
- [src/ometeotl_core/generic/authority.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generic/authority.py)

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
- `validation_summary: JsonMap`
- `logged_at: str`

Methods:
- no custom methods

See also:
- [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)
- [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
