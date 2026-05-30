"""Base model object class for all objects in the Ometeotl/ometeotl_core framework."""

from __future__ import annotations

import bisect
import copy
import json
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    SupportsIndex,
)


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


def _canonical_json_map(
    mapping: Mapping[str, Any] | None,
) -> JsonMap:
    """Return a deterministically ordered plain dict."""
    return dict(sorted(dict(mapping or {}).items()))


def _canonical_json(value: Any) -> str:
    """Return deterministic JSON string for a value (for sorting and hashing)."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Value must be JSON-serializable for deterministic serialization"
        ) from exc


class GuardedJsonDict(dict[str, Any]):
    """Dict wrapper that can reject direct mutations under authority mode."""

    def __init__(
        self,
        initial: Mapping[str, Any] | None,
        mutation_guard: MutationGuard,
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
            super().__setitem__(
                key,
                _wrap_mutable_value(value, self._mutation_guard),
            )

    def __deepcopy__(self, memo: dict[int, Any]) -> dict[str, Any]:
        return {
            copy.deepcopy(key, memo): copy.deepcopy(value, memo)
            for key, value in self.items()
        }


class GuardedJsonList(list[Any]):
    """List wrapper that can reject direct mutations under authority mode."""

    def __init__(
        self,
        initial: List[Any] | None,
        mutation_guard: MutationGuard,
    ):
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

    def __setitem__(self, index: SupportsIndex | slice, value: Any) -> None:
        self._assert_mutation_allowed()
        if isinstance(index, slice):
            wrapped_values = [
                _wrap_mutable_value(item, self._mutation_guard) for item in list(value)
            ]
            super().__setitem__(index, wrapped_values)
            return
        super().__setitem__(
            index,
            _wrap_mutable_value(value, self._mutation_guard),
        )

    def __delitem__(self, index: SupportsIndex | slice) -> None:
        self._assert_mutation_allowed()
        super().__delitem__(index)

    def append(self, value: Any) -> None:
        self._assert_mutation_allowed()
        super().append(_wrap_mutable_value(value, self._mutation_guard))

    def clear(self) -> None:
        self._assert_mutation_allowed()
        super().clear()

    def extend(self, values: Iterable[Any]) -> None:
        self._assert_mutation_allowed()
        super().extend(
            _wrap_mutable_value(value, self._mutation_guard) for value in values
        )

    def insert(self, index: SupportsIndex, value: Any) -> None:
        self._assert_mutation_allowed()
        super().insert(
            index,
            _wrap_mutable_value(value, self._mutation_guard),
        )

    def pop(self, index: SupportsIndex = -1) -> Any:
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

    def __iadd__(self, values: Iterable[Any]) -> "GuardedJsonList":
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


def _require_non_null_value(data: Mapping[str, Any], key: str) -> Any:
    """Read a required field and reject explicit null values."""
    value = data.get(key)
    if value is None:
        raise ValueError(f"Field '{key}' cannot be null")
    return value


def _require_non_null_mapping(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    """Read a required mapping field and reject non-mapping payloads."""
    value = _require_non_null_value(data, key)
    if not isinstance(value, Mapping):
        raise ValueError(f"Field '{key}' must be a mapping")
    return value


def _require_non_null_string(data: Mapping[str, Any], key: str) -> str:
    """Read a required string field and reject explicit null values."""
    return str(_require_non_null_value(data, key))


def _require_non_empty(value: Any, error_message: str) -> None:
    """Raise ValueError when a required value is empty/falsy."""
    if not value:
        raise ValueError(error_message)


def _validated_unit_interval(value: Any, error_message: str) -> float:
    """Validate and normalize a numeric value constrained to [0, 1]."""
    numeric_value = float(value)
    if not 0.0 <= numeric_value <= 1.0:
        raise ValueError(error_message)
    return numeric_value


def _require_in(
    value: Any,
    allowed_values: Collection[Any],
    error_message: str,
) -> None:
    """Raise ValueError when value is not present in the allowed set."""
    if isinstance(allowed_values, (str, bytes)):
        raise TypeError("allowed_values must be a non-string collection")
    if value not in allowed_values:
        raise ValueError(error_message)


def _validated_model_object_kwargs(
    data: Mapping[str, Any],
) -> JsonMap:
    """Validate and normalize common ModelObject payload fields."""
    return {
        "id": _require_non_null_string(data, "id"),
        "object_type": _require_non_null_string(data, "object_type"),
        "schema_version": _validate_schema_version(
            data.get("schema_version")
        ),
        "attributes": _dict_from_data(data, "attributes"),
        "relations": {
            str(key): [str(item) for item in value]
            for key, value in _dict_from_data(
                data, "relations"
            ).items()
        },
        "state": _dict_from_data(data, "state"),
        "context": _dict_from_data(data, "context"),
        "provenance": _dict_from_data(data, "provenance"),
    }


def _base_kwargs_from_typed_payload(
    data: Mapping[str, Any],
    default_object_type: str,
) -> JsonMap:
    """Build normalized base kwargs for a concrete ModelObject subtype."""
    payload = dict(data)
    payload["object_type"] = payload.get("object_type") or default_object_type
    validated = _validated_model_object_kwargs(payload)
    return {
        "id": validated["id"],
        "object_type": validated["object_type"],
        "schema_version": validated["schema_version"],
        "attributes": _deep_plain_copy(validated["attributes"]),
        "relations": _deep_plain_copy(validated["relations"]),
        "state": _deep_plain_copy(validated["state"]),
        "context": _deep_plain_copy(validated["context"]),
        "provenance": _deep_plain_copy(validated["provenance"]),
    }


def _dict_from_data(
    data: Mapping[str, Any], key: str, default: Any = None
) -> JsonMap:
    """Extract a dict field from deserialized data, with null-safe defaults.

    This helper consolidates the common pattern of safely extracting dictionary
    fields during deserialization:
    - If the field is None or missing, returns an empty dict or the default
    - If the field is not a Mapping, returns an empty dict or the default
    - Otherwise returns a plain dict copy of the value

    Usage example:
        metadata = _dict_from_data(data, "metadata")
        # replaces: metadata=dict(data.get("metadata") or {})

    Args:
        data: The source data mapping (typically from from_dict payload)
        key: The field name to extract
        default: Optional default value if field is None/missing/invalid

    Returns:
        A JsonMap (dict[str, Any]) with the extracted value or safe default
    """
    value = data.get(key)
    if value is None or not isinstance(value, Mapping):
        return dict(default) if isinstance(default, Mapping) else {}

    return dict(value)


def _str_from_data(
    data: Mapping[str, Any], key: str, default: str = ""
) -> str:
    """Extract a string field from deserialized data, with null-safe defaults.

    This helper consolidates the common pattern of safely extracting string fields
    during deserialization:
    - If the field is None or missing, returns the provided default
    - Otherwise coerces the value to a string

    Usage example:
        status = _str_from_data(data, "status", "active")
        # replaces: status=str(data.get("status") or "active")

    This pattern is used throughout the model layer for optional string fields
    that have meaningful defaults (F-1, canonical serialization).

    Args:
        data: The source data mapping (typically from from_dict payload)
        key: The field name to extract
        default: The default string value if field is None/missing

    Returns:
        A string with the extracted value or the provided default
    """
    value = data.get(key)
    if value is None or value == "":
        return default

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
        self,
        rel_name: str,
        target_id: ObjectId,
        add: bool = True,
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
            pos = bisect.bisect_left(rel_list, target_id)
            if pos >= len(rel_list) or rel_list[pos] != target_id:
                bisect.insort(rel_list, target_id)
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
            "attributes": _canonical_json_map(self.attributes),
            "relations": {
                key: sorted(str(value) for value in values)
                for key, values in sorted(self.relations.items())
            },
            "state": _canonical_json_map(self.state),
            "context": _canonical_json_map(self.context),
            "provenance": _canonical_json_map(self.provenance),
        }

    def to_llm_view(self) -> JsonMap:
        """Return a language-model-oriented view of this object.

        The implementation is intentionally centralized here so subclasses can
        inherit a consistent export surface while the specialized formatting
        remains in the dedicated IO layer.
        """
        from ometeotl_core.io.llm_export import LLMViewBuilder, LLMViewContext

        builder = LLMViewBuilder()
        context = LLMViewContext()

        object_type = str(self.object_type).lower()
        if object_type == "world":
            return builder.world_view(self, context=context)
        if object_type == "actor":
            return builder.actor_view(self, context=context)
        if object_type == "space":
            return builder.space_view(self, context=context)
        if object_type == "strategy":
            return builder.strategy_view(self, context=context)
        if object_type == "goal":
            return builder.goal_view(self, context=context)
        if object_type == "perception":
            return builder.perception_view(self, context=context)

        view = {
            "id": self.id,
            "type": object_type,
        }
        if self.attributes:
            view["attributes"] = _canonical_json_map(self.attributes)
        if self.state:
            view["state"] = _canonical_json_map(self.state)
        if self.relations:
            view["relations"] = {
                key: sorted(str(value) for value in values)
                for key, values in sorted(self.relations.items())
            }
        return view

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
        return cls(**_validated_model_object_kwargs(data))
