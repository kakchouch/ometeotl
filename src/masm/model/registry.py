"""
The model registry tracks basic objects in the world
and ensures object ids used as parameters for the decorator
methods @relation_methods do exist.
Warning : this registry is not intended to register all objects,
but only those considered minimal for the simulation.
"""

from __future__ import annotations
from typing import Callable, Dict, Optional
from .base import ModelObject, ObjectId


class WorldModelRegistry:
    """World-scoped in-memory registry.

    This registry is intended to support authoritative world operations without
    relying on global mutable state.
    """

    def __init__(self) -> None:
        self._instances: Dict[ObjectId, ModelObject] = {}
        self._mutation_guard: Optional[Callable[[Optional[str]], None]] = None

    def set_mutation_guard(
        self,
        guard: Optional[Callable[[Optional[str]], None]],
    ) -> None:
        """Attach an optional mutation guard callback.

        The callback is expected to raise when mutation is not allowed.
        """
        self._mutation_guard = guard

    def _assert_mutation_allowed(self, authority_token: Optional[str]) -> None:
        if self._mutation_guard is None:
            return
        self._mutation_guard(authority_token)

    def register(self, obj: ModelObject, authority_token: Optional[str] = None) -> None:
        """Register a model object in this world-scoped registry."""
        self._assert_mutation_allowed(authority_token)
        existing = self._instances.get(obj.id)
        if existing is not None and existing is not obj:
            raise ValueError(f"Duplicate model object id: {obj.id}")
        self._instances[obj.id] = obj

    def unregister(
        self, obj_id: ObjectId, authority_token: Optional[str] = None
    ) -> None:
        """Remove an object if the given ID is registered."""
        self._assert_mutation_allowed(authority_token)
        self._instances.pop(obj_id, None)

    def exists(self, obj_id: ObjectId) -> bool:
        """Return True if the given object ID is registered."""
        return obj_id in self._instances

    def get(self, obj_id: ObjectId) -> Optional[ModelObject]:
        """Return the registered object for the given ID, if any."""
        return self._instances.get(obj_id)

    def clear(self) -> None:
        """Clear the registry."""
        self._instances.clear()

    def all_ids(self) -> list[ObjectId]:
        """Return all registered object IDs in sorted order."""
        return sorted(self._instances.keys())


class MinimalModelRegistry:
    """
    Global in-memory registry for minimal objects.
    This registry provides a minimal referential
    integrity layer :
    - register model objects by ID;
    - prevent duplicate live IDs;
    - allow fast existence checks for
        cross-objects relations.
    """

    _instances: Dict[ObjectId, ModelObject] = {}

    @classmethod
    def register(cls, obj: ModelObject) -> None:
        """Register a model object.
        Raises a ValueError if another object
        with the same ID is already registered.
        """
        existing = cls._instances.get(obj.id)
        if existing is not None and existing is not obj:
            raise ValueError("Duplicate model" f"object id : {obj.id}")
        cls._instances[obj.id] = obj

    @classmethod
    def unregister(cls, obj_id: ObjectId) -> None:
        """Remove an object if the given id is
        registered.
        """
        cls._instances.pop(obj_id, None)

    @classmethod
    def exists(cls, obj_id: ObjectId) -> bool:
        """Return True if the given
        object ID is registered"""
        return obj_id in cls._instances

    @classmethod
    def get(cls, obj_id: ObjectId) -> Optional[ModelObject]:
        """Return the registered object for
        the given ID, if any"""
        return cls._instances.get(obj_id)

    @classmethod
    def clear(cls) -> None:
        """Clear the registry.
        Useful for tests and isolated
        scenarios."""
        cls._instances.clear()

    @classmethod
    def all_ids(cls) -> list[ObjectId]:
        """Return all registered object ids
        in sorted order."""
        return sorted(cls._instances.keys())
