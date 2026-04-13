---
title: "CommandResult"
---

Source:
- [src/masm/core/authority.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/core/authority.py)

Local role:
Outcome container returned by [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/) after processing a [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/).

Big-picture role:
Stable contract for accepted/rejected command execution against [World](/ometeotl/documentation/class-reference/model/world/world/).

Inheritance:
- frozen dataclass

Parameters and fields:
- `accepted: bool`
- `reason: str`
- `applied: Optional[JsonMap]`

Methods:
- no custom methods

See also:
- [AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/)
