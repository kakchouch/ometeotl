---
title: "AuthorityCommandHandler"
---

Source:
- [src/ometeotl_core/core/authority.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/core/authority.py)

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
- `validation_soft_gate: bool`
- `validation_policy_profile: str` (`observe_only`, `enforce_structure`, `enforce_domain`)
- `validation_stage_mode_overrides: Optional[Mapping[str, str]]`
- `validation_block_on_error: bool`
- `validation_completeness_level: str`

Methods:
- submit(command: [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)) -> [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
- `close() -> None`
- audit_log -> list[[AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/)]
- internal validation and handler methods for `add_space`, `add_space_relation`, `place_object`, `register_object`, `unregister_object`

Validation behavior:
- Runs a staged validation pipeline before command application when `validation_soft_gate` is enabled.
- Includes syntactic, structural, completeness, temporal, spatial, admissibility, and epistemic validators.
- Exposes structured validation summaries in [CommandResult](/ometeotl/documentation/class-reference/core/command-result/) and [AuditEntry](/ometeotl/documentation/class-reference/core/audit-entry/).
- Can reject commands based on validation errors when `validation_block_on_error=True`.

See also:
- [RuntimeContext](/ometeotl/documentation/class-reference/core/runtime-context/)
- [CommandEnvelope](/ometeotl/documentation/class-reference/core/command-envelope/)
- [CommandResult](/ometeotl/documentation/class-reference/core/command-result/)
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
- [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/)
