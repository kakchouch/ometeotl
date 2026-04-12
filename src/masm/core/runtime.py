"""Runtime bootstrap helpers for local and server-authoritative modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from masm.model.world import World

from .authority import AuthorityCommandHandler


@dataclass
class RuntimeContext:
    """Runtime wiring for a world instance.

    Local mode keeps direct world mutation behavior.
    Server-authoritative mode injects an AuthorityCommandHandler.
    """

    world: World
    authority_handler: Optional[AuthorityCommandHandler] = None

    @property
    def authoritative(self) -> bool:
        """Return True when the runtime uses server authority."""
        return self.authority_handler is not None

    def close(self) -> None:
        """Release runtime resources and locks."""
        if self.authority_handler is not None:
            self.authority_handler.close()


def build_runtime(
    world: World,
    *,
    server_authoritative: bool = False,
    allowed_command_types: Optional[Sequence[str]] = None,
) -> RuntimeContext:
    """Build a runtime context without changing local defaults.

    Authority mode is opt-in only through ``server_authoritative=True``.
    """
    if not server_authoritative:
        return RuntimeContext(world=world, authority_handler=None)

    return RuntimeContext(
        world=world,
        authority_handler=AuthorityCommandHandler(
            world,
            allowed_command_types=allowed_command_types,
        ),
    )
