"""Tests for the world-level IO layer."""

import json

import pytest
import yaml

from masm.io import (
    world_from_json,
    world_from_mapping,
    world_from_yaml,
    world_to_json,
    world_to_yaml,
)
from masm.model.actors import Actor
from masm.model.resources import Resource
from masm.model.space_relations import SpaceRelation
from masm.model.spaces import Space
from masm.model.world import World
from masm.validation import (
    StructuralValidator,
    SyntacticValidator,
    ValidationException,
    ValidationPipeline,
)


def _build_world() -> World:
    world = World(id="world-io-1")
    world.label = "IO Fixture"
    world.add_space(Space(id="zone-a"))
    world.add_space(Space(id="zone-b"))
    world.place_object("actor-1", "zone-a", role="occupies")
    world.add_space_relation(
        SpaceRelation(
            source_space_id="zone-a",
            target_space_id="zone-b",
            relation_type="adjacent_to",
        )
    )

    actor = Actor(id="actor-registered")
    actor.label = "Registered Actor"
    resource = Resource(id="resource-registered")
    resource.kind = "material"
    world.register_object(actor)
    world.register_object(resource)
    return world


def test_world_to_json_is_deterministic():
    """Repeated JSON exports of the same world should match exactly."""
    world = _build_world()

    first = world_to_json(world)
    second = world_to_json(world)

    assert first == second
    assert json.loads(first)["id"] == "world-io-1"


def test_world_json_roundtrip_preserves_graph_and_registry():
    """JSON import/export should preserve world structure and registered types."""
    world = _build_world()

    result = world_from_json(world_to_json(world))

    assert result.parsed_format == "json"
    assert result.validation.valid is True
    assert result.world.id == world.id
    assert result.world.get_space("zone-a") is not None
    assert (
        "actor-1"
        in result.world.space_object_graph.list_objects_in_space(
            "zone-a"
        )
    )
    assert (
        result.world.model_registry.get("actor-registered")
        is not None
    )
    assert isinstance(
        result.world.model_registry.get("actor-registered"),
        Actor,
    )
    assert isinstance(
        result.world.model_registry.get("resource-registered"),
        Resource,
    )


def test_world_yaml_roundtrip_preserves_canonical_payload():
    """YAML import/export should reconstruct the same canonical world payload."""
    world = _build_world()

    yaml_text = world_to_yaml(world)
    result = world_from_yaml(yaml_text)

    assert result.parsed_format == "yaml"
    assert yaml.safe_load(yaml_text) == world.to_dict()
    assert result.world.to_dict() == world.to_dict()


def test_world_from_json_rejects_invalid_payload():
    """Invalid JSON should fail before reconstruction."""
    with pytest.raises(ValueError):
        world_from_json('{"id": "world-io-1",}')


def test_world_from_mapping_raises_validation_exception_for_structural_errors():
    """Structurally invalid mappings should be rejected explicitly."""
    with pytest.raises(ValidationException) as exc_info:
        world_from_mapping(
            {"id": "broken-world", "relations": []}
        )

    assert exc_info.value.result.valid is False
    assert exc_info.value.result.summary["error"] >= 1


def test_world_from_json_aggregates_all_stage_issues_before_raising():
    """All validation stages must run to completion before a ValidationException is raised.

    A syntactically valid JSON that fails structural validation must produce a
    ValidationResult that records execution of both the syntactic and the structural
    stages. Before the fix, the first failing stage raised early and the aggregated
    result was never returned to the caller.
    """
    structurally_invalid_json = (
        '{"id": "broken-world", "relations": []}'
    )
    with pytest.raises(ValidationException) as exc_info:
        world_from_json(
            structurally_invalid_json, raise_on_error=True
        )

    result = exc_info.value.result
    assert result.valid is False
    executed = result.metadata["executed_validators"]
    assert (
        "syntactic" in executed
    ), "Syntactic stage must have run"
    assert (
        "structural" in executed
    ), "Structural stage must have run"
    assert result.summary["error"] >= 1


def test_world_from_json_returns_result_without_raising_when_raise_on_error_false():
    """raise_on_error=False must suppress ValidationException and return the result."""
    structurally_invalid_json = (
        '{"id": "broken-world", "relations": []}'
    )
    result = world_from_json(
        structurally_invalid_json, raise_on_error=False
    )
    assert result.validation.valid is False
    assert result.validation.summary["error"] >= 1


def test_world_from_mapping_skips_syntactic_subclass_validator():
    """Native mapping imports should skip any syntactic-validator subclass."""

    class CustomSyntacticValidator(SyntacticValidator):
        @property
        def name(self) -> str:
            return "syntactic_custom"

    pipeline = ValidationPipeline(
        validators=[
            CustomSyntacticValidator(),
            StructuralValidator(),
        ]
    )

    with pytest.raises(ValidationException) as exc_info:
        world_from_mapping(
            {"id": "broken-world", "relations": []},
            validation_pipeline=pipeline,
            raise_on_error=True,
        )

    executed = exc_info.value.result.metadata[
        "executed_validators"
    ]
    assert "syntactic_custom" not in executed
    assert "structural" in executed


def test_world_json_and_yaml_exports_describe_same_payload():
    """JSON and YAML exports should encode the same canonical mapping."""
    world = _build_world()

    json_payload = json.loads(world_to_json(world))
    yaml_payload = yaml.safe_load(world_to_yaml(world))

    assert json_payload == yaml_payload == world.to_dict()
