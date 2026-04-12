"""Authoritative command boundary for server-owned world mutation.

This module implements a minimal, explicit mutation gateway that can be used
by a server process to apply allowlisted commands while clients remain unable
to mutate ``World`` directly when authority mode is enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence
from uuid import uuid4

from masm.model.base import JsonMap, ModelObject, ObjectId
from masm.model.registry import MinimalModelRegistry
from masm.model.space_relations import SpaceRelation
from masm.model.spaces import Space
from masm.model.world import World


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
        sequence = int(sequence_raw)
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
    ) -> None:
        self.world = world
        self._authority_token = uuid4().hex
        self.world.enable_authority_mode(self._authority_token)
        self.allowed_command_types = tuple(
            allowed_command_types if allowed_command_types is not None
            else (
                "add_space",
                "add_space_relation",
                "place_object",
                "register_object",
                "unregister_object",
            )
        )
        self._processed_command_ids: set[str] = set()
        self._last_sequence_by_actor: Dict[ObjectId, int] = {}
        self._audit_log: list[AuditEntry] = []

    @property
    def audit_log(self) -> list[AuditEntry]:
        """Read-only copy of audit entries."""
        return list(self._audit_log)

    def close(self) -> None:
        """Release authority lock on the world."""
        self.world.disable_authority_mode()

    def submit(self, command: CommandEnvelope) -> CommandResult:
        """Validate minimal structure and apply an allowlisted command."""
        duplicate = command.command_id in self._processed_command_ids
        if duplicate:
            return self._reject(command, "Duplicate command id")

        if command.command_type not in self.allowed_command_types:
            return self._reject(command, "Command type is not allowlisted")

        if not self._actor_exists(command.actor_id):
            return self._reject(command, "Actor id is unknown to minimal registry")

        if not self._is_sequence_valid(command.actor_id, command.sequence):
            return self._reject(command, "Command sequence is not strictly increasing")

        try:
            applied = self._apply_command(command)
        except (KeyError, TypeError, ValueError) as exc:
            return self._reject(command, f"Invalid command payload: {exc}")

        self._processed_command_ids.add(command.command_id)
        self._last_sequence_by_actor[command.actor_id] = command.sequence
        self._audit_log.append(
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
        self._audit_log.append(
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
        return MinimalModelRegistry.exists(actor_id)

    def _is_sequence_valid(self, actor_id: ObjectId, sequence: int) -> bool:
        last_sequence = self._last_sequence_by_actor.get(actor_id, -1)
        return sequence > last_sequence

    def _apply_command(self, command: CommandEnvelope) -> JsonMap:
        if command.command_type == "add_space":
            payload = self._require_payload_fields(command.payload, ("space",))
            space = Space.from_dict(payload["space"])
            self.world.add_space(space, authority_token=self._authority_token)
            return {"space_id": space.id}

        if command.command_type == "add_space_relation":
            payload = self._require_payload_fields(command.payload, ("relation",))
            relation = SpaceRelation.from_dict(payload["relation"])
            self.world.add_space_relation(
                relation,
                authority_token=self._authority_token,
            )
            return {
                "source_space_id": relation.source_space_id,
                "target_space_id": relation.target_space_id,
                "relation_type": relation.relation_type,
            }

        if command.command_type == "place_object":
            payload = self._require_payload_fields(
                command.payload,
                ("object_id", "space_id"),
            )
            role = str(payload.get("role") or "occupies")
            self.world.place_object(
                object_id=str(payload["object_id"]),
                space_id=str(payload["space_id"]),
                role=role,
                authority_token=self._authority_token,
            )
            return {
                "object_id": str(payload["object_id"]),
                "space_id": str(payload["space_id"]),
                "role": role,
            }

        if command.command_type == "register_object":
            payload = self._require_payload_fields(command.payload, ("object",))
            obj = ModelObject.from_dict(payload["object"])
            self.world.register_object(obj, authority_token=self._authority_token)
            return {"object_id": obj.id}

        if command.command_type == "unregister_object":
            payload = self._require_payload_fields(command.payload, ("object_id",))
            object_id = str(payload["object_id"])
            self.world.unregister_object(
                object_id,
                authority_token=self._authority_token,
            )
            return {"object_id": object_id}

        raise ValueError(f"Unsupported command type: {command.command_type}")

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
