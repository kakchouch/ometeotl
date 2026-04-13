---
title: "AuthorityCommandHandler"
---

Source:
- [src/masm/core/authority.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/core/authority.py)

Local role:
Single server-side mutation path that validates and applies allowlisted commands.

Big-picture role:
Authority boundary that locks direct mutation on [World](/ometeotl/documentation/class-reference/model/world/world/), enforces sequencing, handles deduplication, and emits [AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/) records.

Inheritance:
- standard class

Constructor parameters:
- world: [World](/ometeotl/documentation/class-reference/model/world/world/)
- `allowed_command_types: Optional[Sequence[str]]`
- `custom_command_handlers: Optional[Mapping[str, CommandHandler]]`
- `object_factories: Optional[Mapping[str, ObjectFactory]]`
- `audit_log_maxlen: int`
- `processed_ids_maxlen: int`
- `sequence_tracker_max_actors: Optional[int]`
- `sequence_history_max_actors: Optional[int]`

Methods:
- submit(command: [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)) -> [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
- `close() -> None`
- audit_log -> list[[AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/)]
- internal validation and handler methods for `add_space`, `add_space_relation`, `place_object`, `register_object`, `unregister_object`

See also:
- [RuntimeContext](/ometeotl/documentation/class-reference/core/runtime-context/)
- [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)
- [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
- [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/)
