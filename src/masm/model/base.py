"""Base model object class for all objects in the Ometeotl/MASM framework."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping


# NEW: Decorator for auto-generating add/remove methods
def relation_methods(method_name: str, rel_key: str):
    """Decorator to generate add/remove pairs."""

    def decorator(cls):
        def add_method(self, target_id: ObjectId) -> None:
            self._manage_relation(rel_key, target_id, add=True)

        def remove_method(self, target_id: ObjectId) -> None:
            self._manage_relation(rel_key, target_id, add=False)

        add_method.__name__ = f"add_{method_name}"
        remove_method.__name__ = f"remove_{method_name}"
        add_method.__doc__ = f"Adds {method_name} relation."
        remove_method.__doc__ = f"Removes {method_name} relation."

        setattr(cls, add_method.__name__, add_method)
        setattr(cls, remove_method.__name__, remove_method)
        return cls

    return decorator


SchemaVersion = str
ObjectId = str
RelationMap = Dict[str, List[ObjectId]]
JsonMap = Dict[str, Any]
SUPPORTED_SCHEMA_VERSION = "1.0"
MutationGuard = Callable[[], None]


def _wrap_mutable_value(value: Any, mutation_guard: MutationGuard) -> Any:
    if isinstance(value, GuardedJsonDict):
        value.set_mutation_guard(mutation_guard)
        return value
    if isinstance(value, GuardedJsonList):
        value.set_mutation_guard(mutation_guard)
        return value
    if isinstance(value, dict):
        return GuardedJsonDict(value, mutation_guard)
    if isinstance(value, list):
        return GuardedJsonList(value, mutation_guard)
    return value


def _deep_plain_copy(value: Any) -> Any:
    if isinstance(value, GuardedJsonDict):
        return {key: _deep_plain_copy(item) for key, item in value.items()}
    if isinstance(value, GuardedJsonList):
        return [_deep_plain_copy(item) for item in value]
    if isinstance(value, dict):
        return {key: _deep_plain_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_plain_copy(item) for item in value]
    return copy.deepcopy(value)


class GuardedJsonDict(dict[str, Any]):
    """Dict wrapper that can reject direct mutations under authority mode."""

    def __init__(
        self, initial: Mapping[str, Any] | None, mutation_guard: MutationGuard
    ):
        super().__init__()
        self._mutation_guard = mutation_guard
        for key, value in dict(initial or {}).items():
            super().__setitem__(key, _wrap_mutable_value(value, mutation_guard))

    def set_mutation_guard(self, mutation_guard: MutationGuard) -> None:
        self._mutation_guard = mutation_guard
        for key, value in list(super().items()):
            super().__setitem__(key, _wrap_mutable_value(value, mutation_guard))

    def _assert_mutation_allowed(self) -> None:
        self._mutation_guard()

    def __setitem__(self, key: str, value: Any) -> None:
        self._assert_mutation_allowed()
        super().__setitem__(key, _wrap_mutable_value(value, self._mutation_guard))

    def __delitem__(self, key: str) -> None:
        self._assert_mutation_allowed()
        super().__delitem__(key)

    def clear(self) -> None:
        self._assert_mutation_allowed()
        super().clear()

    def pop(self, key: str, default: Any = None) -> Any:
        self._assert_mutation_allowed()
        return super().pop(key, default)

    def popitem(self) -> tuple[str, Any]:
        self._assert_mutation_allowed()
        return super().popitem()

    def setdefault(self, key: str, default: Any = None) -> Any:
        self._assert_mutation_allowed()
        wrapped_default = _wrap_mutable_value(default, self._mutation_guard)
        return super().setdefault(key, wrapped_default)

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._assert_mutation_allowed()
        other = dict(*args, **kwargs)
        for key, value in other.items():
            super().__setitem__(key, _wrap_mutable_value(value, self._mutation_guard))

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        return {
            copy.deepcopy(key, memo): copy.deepcopy(value, memo)
            for key, value in self.items()
        }


class GuardedJsonList(list[Any]):
    """List wrapper that can reject direct mutations under authority mode."""

    def __init__(self, initial: List[Any] | None, mutation_guard: MutationGuard):
        super().__init__(
            _wrap_mutable_value(value, mutation_guard) for value in (initial or [])
        )
        self._mutation_guard = mutation_guard

    def set_mutation_guard(self, mutation_guard: MutationGuard) -> None:
        self._mutation_guard = mutation_guard
        for index, value in enumerate(list(self)):
            super().__setitem__(index, _wrap_mutable_value(value, mutation_guard))

    def _assert_mutation_allowed(self) -> None:
        self._mutation_guard()

    def __setitem__(self, index: int | slice, value: Any) -> None:
        self._assert_mutation_allowed()
        if isinstance(index, slice):
            wrapped_values = [
                _wrap_mutable_value(item, self._mutation_guard) for item in list(value)
            ]
            super().__setitem__(index, wrapped_values)
            return
        super().__setitem__(index, _wrap_mutable_value(value, self._mutation_guard))

    def __delitem__(self, index: int | slice) -> None:
        self._assert_mutation_allowed()
        super().__delitem__(index)

    def append(self, value: Any) -> None:
        self._assert_mutation_allowed()
        super().append(_wrap_mutable_value(value, self._mutation_guard))

    def clear(self) -> None:
        self._assert_mutation_allowed()
        super().clear()

    def extend(self, values: List[Any]) -> None:
        self._assert_mutation_allowed()
        super().extend(
            _wrap_mutable_value(value, self._mutation_guard) for value in values
        )

    def insert(self, index: int, value: Any) -> None:
        self._assert_mutation_allowed()
        super().insert(index, _wrap_mutable_value(value, self._mutation_guard))

    def pop(self, index: int = -1) -> Any:
        self._assert_mutation_allowed()
        return super().pop(index)

    def remove(self, value: Any) -> None:
        self._assert_mutation_allowed()
        super().remove(value)

    def reverse(self) -> None:
        self._assert_mutation_allowed()
        super().reverse()

    def sort(self, *args: Any, **kwargs: Any) -> None:
        self._assert_mutation_allowed()
        super().sort(*args, **kwargs)

    def __iadd__(self, values: List[Any]) -> "GuardedJsonList":
        self._assert_mutation_allowed()
        super().extend(
            _wrap_mutable_value(value, self._mutation_guard) for value in values
        )
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> list[Any]:
        return [copy.deepcopy(value, memo) for value in self]


def _default_schema_version() -> str:
    return SUPPORTED_SCHEMA_VERSION


def _validate_schema_version(value: Any) -> str:
    """Validate schema version and reject incompatible payloads."""
    version = str(value or _default_schema_version())
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported schema_version: "
            f"{version}. Expected {SUPPORTED_SCHEMA_VERSION}"
        )
    return version


def _require_non_null_string(data: Mapping[str, Any], key: str) -> str:
    """Read a required string field and reject explicit null values."""
    value = data.get(key)
    if value is None:
        raise ValueError(f"Field '{key}' cannot be null")
    return str(value)


@dataclass
class ModelObject:
    """A base class for all objects in the model.

    It contains the common fields and methods that all objects share.
    It is voluntarily designed to be as simple as possible, and to be easily
    extendable by subclasses. It should not contain any logic that is specific
    to a particular object_type of object, but rather should be a generic
    container for data that can be used by subclasses. No specific hypothesis
    about the actors, resources, perceptions, objectifs should be included.
    """

    id: ObjectId
    object_type: str
    schema_version: SchemaVersion = field(default_factory=_default_schema_version)
    attributes: JsonMap = field(default_factory=dict)
    relations: RelationMap = field(default_factory=dict)
    state: JsonMap = field(default_factory=dict)
    context: JsonMap = field(default_factory=dict)
    provenance: JsonMap = field(default_factory=dict)
    _mutation_guard: MutationGuard = field(default=lambda: None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Terminal hook for the cooperative __post_init__ chain."""

    def set_mutation_guard(self, mutation_guard: MutationGuard) -> None:
        """Attach a guard used to reject unsanctioned direct mutations."""
        self._mutation_guard = mutation_guard
        self.attributes = _wrap_mutable_value(self.attributes, mutation_guard)
        self.relations = _wrap_mutable_value(self.relations, mutation_guard)
        self.state = _wrap_mutable_value(self.state, mutation_guard)
        self.context = _wrap_mutable_value(self.context, mutation_guard)
        self.provenance = _wrap_mutable_value(self.provenance, mutation_guard)

    def add_relation(self, name: str, target_id: ObjectId) -> None:
        """Add a relation to another object."""
        self._manage_relation(name, target_id, add=True)

    def remove_relation(self, name: str, target_id: ObjectId) -> None:
        """Remove a relation to another object."""
        self._manage_relation(name, target_id, add=False)

    def _manage_relation(
        self, rel_name: str, target_id: ObjectId, add: bool = True
    ) -> None:
        """Generic add/remove for relations. Used by subclasses."""
        if not rel_name:
            raise ValueError("Relation name cannot be empty")
        if not target_id:
            raise ValueError("Target ID cannot be empty")

        if rel_name not in self.relations:
            self.relations[rel_name] = []

        rel_list: List[ObjectId] = self.relations[rel_name]
        if add:
            if target_id not in rel_list:
                rel_list.append(target_id)
                rel_list.sort()  # Keep sorted for determinism
        else:
            if target_id in rel_list:
                rel_list.remove(target_id)
                if not rel_list:
                    del self.relations[rel_name]

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the object."""
        if not key:
            raise ValueError("Attribute key cannot be empty")
        self.attributes[key] = value

    def set_state(self, key: str, value: Any) -> None:
        """Set a state value on the object."""
        if not key:
            raise ValueError("State key cannot be empty")
        self.state[key] = value

    def set_provenance(self, key: str, value: Any) -> None:
        """Set a provenance value on the object."""
        if not key:
            raise ValueError("Provenance key cannot be empty")
        self.provenance[key] = value

    def add_to_attribute_list(self, attr_name: str, item: Any) -> None:
        """Add an item to a list attribute, avoiding duplicates."""
        if not attr_name:
            raise ValueError("Attribute name cannot be empty")
        if item is None or (isinstance(item, str) and not item):
            raise ValueError("Item cannot be empty")
        lst = self.attributes.get(attr_name, [])
        if item not in lst:
            lst.append(item)
            # Sort if all strings
            if lst and all(isinstance(x, str) for x in lst):
                lst.sort()
            self.attributes[attr_name] = lst

    def remove_from_attribute_list(self, attr_name: str, item: Any) -> None:
        """Remove an item from a list attribute."""
        if not attr_name:
            raise ValueError("Attribute name cannot be empty")
        lst = self.attributes.get(attr_name, [])
        if item in lst:
            lst.remove(item)
            if not lst:
                self.attributes.pop(attr_name, None)
            else:
                self.attributes[attr_name] = lst

    def to_dict(self) -> JsonMap:
        """Convert the object to a dictionary representation."""
        return {
            "id": self.id,
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "attributes": dict(sorted(self.attributes.items())),
            "relations": {
                key: sorted(str(value) for value in values)
                for key, values in sorted(self.relations.items())
            },
            "state": dict(sorted(self.state.items())),
            "context": dict(sorted(self.context.items())),
            "provenance": dict(sorted(self.provenance.items())),
        }

    def _base_kwargs(self) -> "JsonMap":
        """Return the base keyword arguments shared by all ModelObject subclasses.

        Intended for use inside subclass ``from_dict`` implementations to avoid
        repeating the eight common field assignments.
        """
        return {
            "id": self.id,
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "attributes": _deep_plain_copy(self.attributes),
            "relations": _deep_plain_copy(self.relations),
            "state": _deep_plain_copy(self.state),
            "context": _deep_plain_copy(self.context),
            "provenance": _deep_plain_copy(self.provenance),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ModelObject":
        return cls(
            id=_require_non_null_string(data, "id"),
            object_type=_require_non_null_string(data, "object_type"),
            schema_version=_validate_schema_version(data.get("schema_version")),
            attributes=dict(data.get("attributes") or {}),
            relations={
                str(key): [str(item) for item in value]
                for key, value in dict(data.get("relations") or {}).items()
            },
            state=dict(data.get("state") or {}),
            context=dict(data.get("context") or {}),
            provenance=dict(data.get("provenance") or {}),
        )
