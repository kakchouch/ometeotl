"""
This module defines the World class.

World inherits from Space and represents the root semantic space of the
model. It provides the primary ontological layer in which the simulation
is grounded. A world may operate as a standalone space or support the
existence of other derived or nested spaces.

Objects directly supported by a world are treated as minimal objects and
    must be registered in the world-scoped registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional
from .base import (
    JsonMap,
    ObjectId,
    ModelObject,
    _base_kwargs_from_typed_payload,
    _dict_from_data,
    _require_non_empty,
)
from .spaces import (
    Space,
    SpaceObjectGraph,
    SpaceObjectMembership,
)
from .space_relations import SpaceRelation, SpaceRelationGraph
from .registry import WorldModelRegistry

SpaceId = str


@dataclass
class World(Space):
    """
    World inherits from Space and represents the root semantic space of the
    model. It provides the primary ontological layer in which the simulation
    is grounded. A world may operate as a standalone space or support the
    existence of other derived or nested spaces.

    Objects directly supported by a world are treated as minimal objects and
    must be registered in the world-scoped registry.
    """

    object_type: str = "world"
    is_root_world: bool = True
    space_object_graph: SpaceObjectGraph = field(default_factory=SpaceObjectGraph)
    space_relation_graph: SpaceRelationGraph = field(default_factory=SpaceRelationGraph)
    model_registry: WorldModelRegistry = field(default_factory=WorldModelRegistry)
    _authority_mode_enabled: bool = field(default=False, init=False, repr=False)
    _authority_token: Optional[str] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.object_type = "world"
        self.attributes["kind"] = "world"
        self.attributes["is_root_world"] = self.is_root_world
        self.model_registry.set_mutation_guard(self._assert_mutation_allowed)
        self.set_mutation_guard(self._assert_bound_object_mutation_allowed)
        self._bind_existing_objects()

    def _assert_bound_object_mutation_allowed(self) -> None:
        self._assert_mutation_allowed(None)

    def _bind_existing_objects(self) -> None:
        for space in self.space_object_graph.spaces.values():
            space.set_mutation_guard(self._assert_bound_object_mutation_allowed)
        for obj_id in self.model_registry.all_ids():
            obj = self.model_registry.get(obj_id)
            if obj is not None:
                obj.set_mutation_guard(self._assert_bound_object_mutation_allowed)

    def enable_authority_mode(self, token: str) -> None:
        """Enable authoritative mutation mode.

        When enabled, mutating world APIs only accept calls that carry the
        expected authority token. This creates an explicit server-side
        boundary while keeping backward compatibility for local/in-process use
        when authority mode is disabled.
        """
        _require_non_empty(token, "Authority token cannot be empty")
        if self._authority_mode_enabled:
            raise RuntimeError("Authority mode is already enabled for this world")
        self._authority_mode_enabled = True
        self._authority_token = token

    def disable_authority_mode(self) -> None:
        """Disable authoritative mutation mode."""
        self._authority_mode_enabled = False
        self._authority_token = None

    def _assert_mutation_allowed(self, authority_token: Optional[str]) -> None:
        if not self._authority_mode_enabled:
            return
        if authority_token != self._authority_token:
            raise PermissionError(
                "World mutation denied: use the authoritative command interface"
            )

    # --- Sub-space management -----------------------------------------------

    def add_space(self, space: Space, authority_token: Optional[str] = None) -> None:
        """Add a sub-space to this world's space object graph."""
        self._assert_mutation_allowed(authority_token)
        self.space_object_graph.add_space(space)
        space.set_mutation_guard(self._assert_bound_object_mutation_allowed)

    def get_space(self, space_id: SpaceId) -> Optional[Space]:
        """Retrieve a sub-space by ID, or None if it does not exist."""
        return self.space_object_graph.get_space(space_id)

    def add_space_relation(
        self,
        relation: SpaceRelation,
        authority_token: Optional[str] = None,
    ) -> None:
        """Add a directional or symmetric relation between two sub-spaces."""
        self._assert_mutation_allowed(authority_token)
        self.space_relation_graph.add_relation(relation)

    # --- Object placement ---------------------------------------------------

    def place_object(
        self,
        object_id: ObjectId,
        space_id: SpaceId,
        role: str = "occupies",
        authority_token: Optional[str] = None,
    ) -> None:
        """Declare the presence of an object in a given sub-space.

        The target space must have been added to this world beforehand via
        ``add_space``.
        """
        self._assert_mutation_allowed(authority_token)
        membership = SpaceObjectMembership(
            object_id=object_id,
            space_id=space_id,
            role=role,
        )
        self.space_object_graph.add_object_membership(membership)

    # --- Registry operations ------------------------------------------------

    def register_object(
        self,
        obj: ModelObject,
        authority_token: Optional[str] = None,
    ) -> None:
        """Register a minimal object in this world-scoped registry."""
        self._assert_mutation_allowed(authority_token)
        self.model_registry.register(obj, authority_token=authority_token)
        obj.set_mutation_guard(self._assert_bound_object_mutation_allowed)

    def unregister_object(
        self,
        obj_id: ObjectId,
        authority_token: Optional[str] = None,
    ) -> None:
        """Remove an object from this world-scoped registry."""
        self._assert_mutation_allowed(authority_token)
        self.model_registry.unregister(obj_id, authority_token=authority_token)

    def is_space_abstract(self, space_id: SpaceId) -> bool:
        """Check whether a sub-space is marked as abstract.

        Returns True if the space exists and has ``is_abstract == True``,
        False otherwise.
        """
        space = self.get_space(space_id)
        return space.is_abstract if space is not None else False

    # --- Convenience Wrappers ------------------------------------------------
    def add_object_to_space(
        self,
        obj,
        space_id,
        role="occupies",
        authority_token: Optional[str] = None,
    ) -> None:
        """Register an object and place it in a sub-space in one step.

        This is a convenience method that ensures the object is registered
        before being placed in the specified sub-space.
        """
        self.register_object(obj, authority_token=authority_token)
        self.place_object(
            obj.id,
            space_id,
            role=role,
            authority_token=authority_token,
        )

    # --- Serialization ------------------------------------------------------

    def to_dict(self) -> JsonMap:
        """Canonical serialization of the world.

        Extends the base Space serialization with sub-space graph data
        (SpaceObjectGraph and SpaceRelationGraph). Satisfies F-1, F-2, F-3.
        """
        base = super().to_dict()
        base["space_object_graph"] = self.space_object_graph.to_dict()
        base["space_relation_graph"] = self.space_relation_graph.to_dict()
        base["model_registry"] = self.model_registry.to_dict()
        return base

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "World":
        """Reconstruct a World from its canonical dictionary representation."""
        base_kwargs = _base_kwargs_from_typed_payload(data, "world")
        attributes = _dict_from_data(base_kwargs, "attributes")
        is_root_world = bool(attributes.get("is_root_world", True))
        return cls(
            **base_kwargs,
            is_root_world=is_root_world,
            space_object_graph=SpaceObjectGraph.from_dict(
                data.get("space_object_graph") or {}
            ),
            space_relation_graph=SpaceRelationGraph.from_dict(
                data.get("space_relation_graph") or {}
            ),
            model_registry=WorldModelRegistry.from_dict(
                data.get("model_registry") or {}
            ),
        )

    @classmethod
    def from_context(cls, context: Mapping[str, Any]) -> "World":
        """Build a world from contextual payload via generation pipeline."""
        from ometeotl_core.generation import (
            ContextualGenerationPipeline,
            GenerationContext,
            GenerationPlacement,
        )
        from ometeotl_core.validation import (
            StructuralValidator,
            ValidationException,
            ValidationPipeline,
        )

        payload = dict(context)
        world_id = str(payload.get("id") or "")
        if not world_id:
            raise ValueError("World.from_context requires non-empty 'id'")

        def _parse_contexts(raw_contexts: Any, kind: str) -> list[GenerationContext]:
            parsed: list[GenerationContext] = []
            for entry in raw_contexts or []:
                if isinstance(entry, GenerationContext):
                    parsed.append(entry)
                    continue
                if not isinstance(entry, Mapping):
                    raise TypeError(
                        f"World.from_context expected mapping for nested '{kind}' context"
                    )
                nested_payload = dict(entry)
                nested_id = str(nested_payload.get("id") or "")
                if not nested_id:
                    raise ValueError(
                        f"World.from_context requires non-empty nested '{kind}' id"
                    )
                parsed.append(
                    GenerationContext(
                        kind=str(nested_payload.get("kind") or kind),
                        id=nested_id,
                        label=str(nested_payload.get("label") or ""),
                        attributes=dict(nested_payload.get("attributes") or {}),
                        relations={
                            str(name): [str(item) for item in values or []]
                            for name, values in dict(
                                nested_payload.get("relations") or {}
                            ).items()
                        },
                        state=dict(nested_payload.get("state") or {}),
                        context=dict(nested_payload.get("context") or {}),
                        provenance=dict(nested_payload.get("provenance") or {}),
                        metadata=dict(nested_payload.get("metadata") or {}),
                        validate=bool(nested_payload.get("validate", True)),
                        validation_mode=str(
                            nested_payload.get("validation_mode") or "strict"
                        ),
                        stage_modes=dict(nested_payload.get("stage_modes") or {}),
                    )
                )
            return parsed

        placements: list[GenerationPlacement] = []
        for entry in payload.get("placements") or []:
            if isinstance(entry, GenerationPlacement):
                placements.append(entry)
                continue
            if not isinstance(entry, Mapping):
                raise TypeError("World.from_context expected mapping for 'placements'")
            placement_payload = dict(entry)
            object_id = str(placement_payload.get("object_id") or "").strip()
            space_id = str(placement_payload.get("space_id") or "").strip()
            if not object_id or not space_id:
                raise ValueError(
                    "World.from_context placements require non-empty 'object_id' and 'space_id'"
                )
            placements.append(
                GenerationPlacement(
                    object_id=object_id,
                    space_id=space_id,
                    role=str(placement_payload.get("role") or "occupies"),
                    metadata=dict(placement_payload.get("metadata") or {}),
                )
            )

        generation_context = GenerationContext(
            kind="world",
            id=world_id,
            label=str(payload.get("label") or ""),
            attributes=dict(payload.get("attributes") or {}),
            relations={
                str(name): [str(item) for item in values or []]
                for name, values in dict(payload.get("relations") or {}).items()
            },
            state=dict(payload.get("state") or {}),
            context=dict(payload.get("context") or {}),
            provenance=dict(payload.get("provenance") or {}),
            metadata=dict(payload.get("metadata") or {}),
            spaces=_parse_contexts(payload.get("spaces"), "space"),
            actors=_parse_contexts(payload.get("actors"), "actor"),
            resources=_parse_contexts(payload.get("resources"), "resource"),
            placements=placements,
            validate=bool(payload.get("validate", True)),
            validation_mode=str(payload.get("validation_mode") or "strict"),
            stage_modes=dict(payload.get("stage_modes") or {}),
        )

        pipeline = ContextualGenerationPipeline(
            validation_pipeline=ValidationPipeline(validators=[StructuralValidator()])
        )
        result = pipeline.generate(generation_context)
        if result.validation is not None and not result.validation.valid:
            raise ValidationException(result.validation)
        if not isinstance(result.generated, cls):
            raise TypeError(
                f"World.from_context expected generated World, got {type(result.generated).__name__}"
            )
        return result.generated
