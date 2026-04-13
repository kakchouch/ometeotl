---
title: "CommandEnvelope"
---

Source:
- [src/masm/core/authority.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/core/authority.py)

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

See also:
- [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
- [AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/)
