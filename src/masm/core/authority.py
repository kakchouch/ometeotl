"""Authoritative command boundary for server-owned world mutation.

This module implements a minimal, explicit mutation gateway that can be used
by a server process to apply allowlisted commands while clients remain unable
to mutate ``World`` directly when authority mode is enabled.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
from typing import Any, Callable, Mapping, Optional, Sequence
from uuid import uuid4

from masm.model.actions import Action
from masm.model.actors import Actor
from masm.model.base import JsonMap, ModelObject, ObjectId
from masm.model.objects import GenericObject
from masm.model.resources import Resource
from masm.model.space_relations import SpaceRelation
from masm.model.spaces import Space
from masm.model.world import World

ObjectFactory = Callable[[Mapping[str, Any]], ModelObject]
CommandHandler = Callable[["CommandEnvelope", World, str], JsonMap]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CommandEnvelope:
    """Canonical command payload accepted by the authority boundary."""

    command_id: str
    actor_id: ObjectId
    command_type: str
    payload: JsonMap = field(default_factory=dict)
    sequence: int = 0
    issued_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> JsonMap:
        """Canonical serialization for transport and logs."""
        return {
            "command_id": self.command_id,
            "actor_id": self.actor_id,
            "command_type": self.command_type,
            "payload": dict(sorted(self.payload.items())),
            "sequence": self.sequence,
            "issued_at": self.issued_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CommandEnvelope":
        """Build a command envelope from mapping data."""
        command_id = str(data.get("command_id") or "")
        actor_id = str(data.get("actor_id") or "")
        command_type = str(data.get("command_type") or "")
        if not command_id:
            raise ValueError("Command id cannot be empty")
        if not actor_id:
            raise ValueError("Actor id cannot be empty")
        if not command_type:
            raise ValueError("Command type cannot be empty")
        sequence_raw = data.get("sequence", 0)
        try:
            sequence = int(sequence_raw) if sequence_raw is not None else 0
        except (TypeError, ValueError) as exc:
            raise ValueError("Command sequence must be a valid integer") from exc
        if sequence < 0:
            raise ValueError("Command sequence cannot be negative")
        return cls(
            command_id=command_id,
            actor_id=actor_id,
            command_type=command_type,
            payload=dict(data.get("payload") or {}),
            sequence=sequence,
            issued_at=str(data.get("issued_at") or _utc_now_iso()),
        )


@dataclass(frozen=True)
class CommandResult:
    """Result of command processing at the authority boundary."""

    accepted: bool
    reason: str = ""
    applied: Optional[JsonMap] = None


@dataclass(frozen=True)
class AuditEntry:
    """Immutable audit record for accepted/rejected commands."""

    command_id: str
    actor_id: ObjectId
    command_type: str
    sequence: int
    accepted: bool
    reason: str
    logged_at: str = field(default_factory=_utc_now_iso)


class AuthorityCommandHandler:
    """Single mutation path for authoritative world updates.

    The handler enforces minimal structural checks and an allowlist of command
    types. Domain admissibility validation (resources, advanced prerequisites,
    conflict resolution) is intentionally deferred to later validation layers.
    """

    SYSTEM_ACTOR_ID = "system"

    def __init__(
        self,
        world: World,
        allowed_command_types: Optional[Sequence[str]] = None,
        custom_command_handlers: Optional[Mapping[str, CommandHandler]] = None,
        object_factories: Optional[Mapping[str, ObjectFactory]] = None,
        audit_log_maxlen: int = 1000,
        processed_ids_maxlen: int = 10000,
        sequence_tracker_max_actors: Optional[int] = 1000,
        sequence_history_max_actors: Optional[int] = None,
    ) -> None:
        if audit_log_maxlen <= 0:
            raise ValueError("audit_log_maxlen must be greater than 0")
        if processed_ids_maxlen <= 0:
            raise ValueError("processed_ids_maxlen must be greater than 0")
        if sequence_tracker_max_actors is not None and sequence_tracker_max_actors <= 0:
            raise ValueError("sequence_tracker_max_actors must be greater than 0")
        if sequence_history_max_actors is not None and sequence_history_max_actors <= 0:
            raise ValueError("sequence_history_max_actors must be greater than 0")

        resolved_sequence_history_max_actors = (
            sequence_history_max_actors
            if sequence_history_max_actors is not None
            else processed_ids_maxlen
        )
        if (
            sequence_tracker_max_actors is not None
            and sequence_tracker_max_actors > resolved_sequence_history_max_actors
        ):
            raise ValueError(
                "sequence_tracker_max_actors cannot exceed "
                "sequence_history_max_actors"
            )

        self.world = world
        self._authority_token = uuid4().hex
        self._command_handlers: dict[str, CommandHandler] = {
            "add_space": self._handle_add_space,
            "add_space_relation": self._handle_add_space_relation,
            "place_object": self._handle_place_object,
            "register_object": self._handle_register_object,
            "unregister_object": self._handle_unregister_object,
        }
        if custom_command_handlers:
            self._command_handlers.update(custom_command_handlers)
        self.allowed_command_types = tuple(
            allowed_command_types
            if allowed_command_types is not None
            else tuple(self._command_handlers.keys())
        )
        unsupported_allowed_types = [
            command_type
            for command_type in self.allowed_command_types
            if command_type not in self._command_handlers
        ]
        if unsupported_allowed_types:
            unsupported = ", ".join(sorted(unsupported_allowed_types))
            raise ValueError(
                "Allowed command type has no registered handler: " f"{unsupported}"
            )
        self._object_factories: dict[str, ObjectFactory] = self._default_object_factories()
        if object_factories:
            self._object_factories.update(
                {
                    str(type_name).lower(): factory
                    for type_name, factory in object_factories.items()
                }
            )
        self._audit_log: deque[AuditEntry] = deque(maxlen=audit_log_maxlen)
        self._processed_ids_maxlen = processed_ids_maxlen
        self._sequence_tracker_max_actors = sequence_tracker_max_actors
        self._sequence_history_max_actors = resolved_sequence_history_max_actors
        self._processed_command_ids: set[str] = set()
        self._processed_command_order: deque[str] = deque()
        # First-come tracker: existing actors keep their sequence slot.
        self._last_sequence_by_actor: dict[ObjectId, int] = {}
        self._retired_sequence_by_actor: OrderedDict[ObjectId, int] = OrderedDict()
        self._active_tracked_actor_ids: set[ObjectId] = set()
        self._lock = threading.Lock()
        self._closed = False
        # Lock activation is the final init step to avoid partial-init lock side effects.
        self.world.enable_authority_mode(self._authority_token)

    @property
    def audit_log(self) -> list[AuditEntry]:
        """Read-only copy of audit entries."""
        with self._lock:
            return list(self._audit_log)

    def close(self) -> None:
        """Release authority lock on the world."""
        with self._lock:
            if self._closed:
                return
            self.world.disable_authority_mode()
            self._closed = True

    def submit(self, command: CommandEnvelope) -> CommandResult:
        """Validate minimal structure and apply an allowlisted command."""
        with self._lock:
            if self._closed:
                return self._reject(command, "Command handler is closed")

            duplicate = command.command_id in self._processed_command_ids
            if duplicate:
                return self._reject(command, "Duplicate command id")

            if command.command_type not in self.allowed_command_types:
                return self._reject(command, "Command type is not allowlisted")

            if not self._actor_exists(command.actor_id):
                return self._reject(
                    command,
                    "Actor id is unknown to this world registry",
                )

            if not self._is_sequence_valid(command.actor_id, command.sequence):
                return self._reject(
                    command,
                    "Command sequence is not strictly increasing",
                )

            if not self._has_sequence_capacity(command.actor_id):
                return self._reject(
                    command,
                    "Sequence tracker capacity reached for new actor",
                )

            try:
                applied = self._apply_command(command)
            except (KeyError, TypeError, ValueError) as exc:
                return self._reject(command, f"Invalid command payload: {exc}")

            self._mark_processed(command.command_id)
            self._set_last_sequence(command.actor_id, command.sequence)
            self._append_audit(
                AuditEntry(
                    command_id=command.command_id,
                    actor_id=command.actor_id,
                    command_type=command.command_type,
                    sequence=command.sequence,
                    accepted=True,
                    reason="accepted",
                )
            )
            return CommandResult(accepted=True, applied=applied)

    def _reject(self, command: CommandEnvelope, reason: str) -> CommandResult:
        self._append_audit(
            AuditEntry(
                command_id=command.command_id,
                actor_id=command.actor_id,
                command_type=command.command_type,
                sequence=command.sequence,
                accepted=False,
                reason=reason,
            )
        )
        return CommandResult(accepted=False, reason=reason)

    def _actor_exists(self, actor_id: ObjectId) -> bool:
        if actor_id == self.SYSTEM_ACTOR_ID:
            return True
        return self.world.model_registry.exists(actor_id)

    def _is_sequence_valid(self, actor_id: ObjectId, sequence: int) -> bool:
        last_active_sequence = self._last_sequence_by_actor.get(actor_id, -1)
        last_retired_sequence = self._retired_sequence_by_actor.get(actor_id, -1)
        return sequence > max(last_active_sequence, last_retired_sequence)

    def _has_sequence_capacity(self, actor_id: ObjectId) -> bool:
        if actor_id == self.SYSTEM_ACTOR_ID:
            return True
        if actor_id in self._active_tracked_actor_ids:
            return True

        limit = self._sequence_tracker_max_actors
        if limit is not None and len(self._active_tracked_actor_ids) >= limit:
            return False

        if actor_id in self._last_sequence_by_actor:
            return True
        if actor_id in self._retired_sequence_by_actor:
            return True

        return self._sequence_entry_count() < self._sequence_history_max_actors

    def _mark_processed(self, command_id: str) -> None:
        self._processed_command_ids.add(command_id)
        self._processed_command_order.append(command_id)
        while len(self._processed_command_order) > self._processed_ids_maxlen:
            expired_command_id = self._processed_command_order.popleft()
            self._processed_command_ids.discard(expired_command_id)

    def _set_last_sequence(self, actor_id: ObjectId, sequence: int) -> None:
        self._retired_sequence_by_actor.pop(actor_id, None)
        if actor_id in self._last_sequence_by_actor:
            self._last_sequence_by_actor[actor_id] = sequence
            if actor_id != self.SYSTEM_ACTOR_ID:
                self._active_tracked_actor_ids.add(actor_id)
            return
        self._last_sequence_by_actor[actor_id] = sequence
        if actor_id != self.SYSTEM_ACTOR_ID:
            self._active_tracked_actor_ids.add(actor_id)

    def _sequence_entry_count(self) -> int:
        return len(self._last_sequence_by_actor) + len(self._retired_sequence_by_actor)

    def _remember_retired_sequence(self, actor_id: ObjectId, sequence: int) -> None:
        self._retired_sequence_by_actor.pop(actor_id, None)
        self._retired_sequence_by_actor[actor_id] = sequence
        while self._sequence_entry_count() > self._sequence_history_max_actors:
            self._retired_sequence_by_actor.popitem(last=False)

    def _append_audit(self, entry: AuditEntry) -> None:
        self._audit_log.append(entry)

    def _apply_command(self, command: CommandEnvelope) -> JsonMap:
        command_handler = self._command_handlers.get(command.command_type)
        if command_handler is None:
            raise ValueError(f"Unsupported command type: {command.command_type}")
        return command_handler(command, self.world, self._authority_token)

    def _handle_add_space(
        self,
        command: CommandEnvelope,
        world: World,
        authority_token: str,
    ) -> JsonMap:
        payload = self._require_payload_fields(command.payload, ("space",))
        space = self._reconstruct_registered_object(payload["space"])
        if not isinstance(space, Space):
            raise ValueError(
                "Payload does not describe a Space "
                f"(got {type(space).__name__})"
            )
        world.add_space(space, authority_token=authority_token)
        return {"space_id": space.id}

    def _handle_add_space_relation(
        self,
        command: CommandEnvelope,
        world: World,
        authority_token: str,
    ) -> JsonMap:
        payload = self._require_payload_fields(command.payload, ("relation",))
        relation = SpaceRelation.from_dict(payload["relation"])
        world.add_space_relation(relation, authority_token=authority_token)
        return {
            "source_space_id": relation.source_space_id,
            "target_space_id": relation.target_space_id,
            "relation_type": relation.relation_type,
        }

    def _handle_place_object(
        self,
        command: CommandEnvelope,
        world: World,
        authority_token: str,
    ) -> JsonMap:
        payload = self._require_payload_fields(
            command.payload,
            ("object_id", "space_id"),
        )
        role = str(payload.get("role") or "occupies")
        world.place_object(
            object_id=str(payload["object_id"]),
            space_id=str(payload["space_id"]),
            role=role,
            authority_token=authority_token,
        )
        return {
            "object_id": str(payload["object_id"]),
            "space_id": str(payload["space_id"]),
            "role": role,
        }

    def _handle_register_object(
        self,
        command: CommandEnvelope,
        world: World,
        authority_token: str,
    ) -> JsonMap:
        payload = self._require_payload_fields(command.payload, ("object",))
        obj = self._reconstruct_registered_object(payload["object"])
        world.register_object(obj, authority_token=authority_token)
        return {"object_id": obj.id}

    @staticmethod
    def _default_object_factories() -> dict[str, ObjectFactory]:
        return {
            "action": Action.from_dict,
            "actor": Actor.from_dict,
            "generic": GenericObject.from_dict,
            "resource": Resource.from_dict,
            "space": Space.from_dict,
            "world": World.from_dict,
        }

    def _reconstruct_registered_object(self, raw_object: Mapping[str, Any]) -> ModelObject:
        object_payload = dict(raw_object)
        object_type = str(object_payload.get("object_type") or "").lower()
        factory = self._object_factories.get(object_type, ModelObject.from_dict)
        return factory(object_payload)

    def _handle_unregister_object(
        self,
        command: CommandEnvelope,
        world: World,
        authority_token: str,
    ) -> JsonMap:
        payload = self._require_payload_fields(command.payload, ("object_id",))
        object_id = str(payload["object_id"])
        last_sequence = self._last_sequence_by_actor.pop(object_id, None)
        if last_sequence is not None:
            self._remember_retired_sequence(object_id, last_sequence)
        world.unregister_object(object_id, authority_token=authority_token)
        self._active_tracked_actor_ids.discard(object_id)
        return {"object_id": object_id}

    @staticmethod
    def _require_payload_fields(
        payload: Mapping[str, Any],
        fields: Sequence[str],
    ) -> JsonMap:
        missing = [
            field_name for field_name in fields if payload.get(field_name) is None
        ]
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise ValueError(f"Missing required payload field(s): {missing_str}")
        return dict(payload)
