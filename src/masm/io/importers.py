"""Canonical import helpers for the IO layer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from masm.model.world import World
from masm.validation import (
    MODE_STRICT,
    SyntacticValidator,
    StructuralValidator,
    ValidationContext,
    ValidationException,
    ValidationPipeline,
    ValidationResult,
)

SUPPORTED_WORLD_INPUT_FORMATS: frozenset[str] = frozenset(
    {"json", "yaml", "auto"}
)


@dataclass(frozen=True)
class WorldImportResult:
    """Result bundle returned by world import helpers."""

    world: World
    validation: ValidationResult
    payload: dict[str, Any]
    parsed_format: str


def world_from_mapping(
    payload: Mapping[str, Any],
    *,
    validation_pipeline: ValidationPipeline | None = None,
    mode: str = MODE_STRICT,
    stage_modes: Mapping[str, str] | None = None,
    raise_on_error: bool = True,
) -> WorldImportResult:
    """Validate and reconstruct a world from a canonical mapping payload."""
    native_payload = dict(payload)
    validation = _validate_world_payload(
        serialized_payload=native_payload,
        parsed_payload=native_payload,
        source_format="native",
        validation_pipeline=validation_pipeline,
        mode=mode,
        stage_modes=stage_modes,
    )
    if raise_on_error and not validation.valid:
        raise ValidationException(validation)
    return WorldImportResult(
        world=World.from_dict(native_payload),
        validation=validation,
        payload=native_payload,
        parsed_format="native",
    )


def world_from_json(
    payload: str | bytes,
    *,
    validation_pipeline: ValidationPipeline | None = None,
    mode: str = MODE_STRICT,
    stage_modes: Mapping[str, str] | None = None,
    raise_on_error: bool = True,
) -> WorldImportResult:
    """Validate and reconstruct a world from JSON text."""
    return _world_from_serialized(
        payload,
        format_hint="json",
        validation_pipeline=validation_pipeline,
        mode=mode,
        stage_modes=stage_modes,
        raise_on_error=raise_on_error,
    )


def world_from_yaml(
    payload: str | bytes,
    *,
    validation_pipeline: ValidationPipeline | None = None,
    mode: str = MODE_STRICT,
    stage_modes: Mapping[str, str] | None = None,
    raise_on_error: bool = True,
) -> WorldImportResult:
    """Validate and reconstruct a world from YAML text."""
    return _world_from_serialized(
        payload,
        format_hint="yaml",
        validation_pipeline=validation_pipeline,
        mode=mode,
        stage_modes=stage_modes,
        raise_on_error=raise_on_error,
    )


def read_world_json(
    path: str | Path,
    *,
    validation_pipeline: ValidationPipeline | None = None,
    mode: str = MODE_STRICT,
    stage_modes: Mapping[str, str] | None = None,
    raise_on_error: bool = True,
) -> WorldImportResult:
    """Read, validate, and reconstruct a world from a JSON file."""
    return world_from_json(
        Path(path).read_text(encoding="utf-8"),
        validation_pipeline=validation_pipeline,
        mode=mode,
        stage_modes=stage_modes,
        raise_on_error=raise_on_error,
    )


def read_world_yaml(
    path: str | Path,
    *,
    validation_pipeline: ValidationPipeline | None = None,
    mode: str = MODE_STRICT,
    stage_modes: Mapping[str, str] | None = None,
    raise_on_error: bool = True,
) -> WorldImportResult:
    """Read, validate, and reconstruct a world from a YAML file."""
    return world_from_yaml(
        Path(path).read_text(encoding="utf-8"),
        validation_pipeline=validation_pipeline,
        mode=mode,
        stage_modes=stage_modes,
        raise_on_error=raise_on_error,
    )


def _world_from_serialized(
    payload: str | bytes,
    *,
    format_hint: str,
    validation_pipeline: ValidationPipeline | None,
    mode: str,
    stage_modes: Mapping[str, str] | None,
    raise_on_error: bool,
) -> WorldImportResult:
    raw_text = _coerce_text(payload)
    parsed_payload, parsed_format = _parse_world_payload(
        raw_text, format_hint
    )
    validation = _validate_world_payload(
        serialized_payload=raw_text,
        parsed_payload=parsed_payload,
        source_format=parsed_format,
        validation_pipeline=validation_pipeline,
        mode=mode,
        stage_modes=stage_modes,
    )
    if raise_on_error and not validation.valid:
        raise ValidationException(validation)
    return WorldImportResult(
        world=World.from_dict(parsed_payload),
        validation=validation,
        payload=parsed_payload,
        parsed_format=parsed_format,
    )


def _validate_world_payload(
    *,
    serialized_payload: str | Mapping[str, Any],
    parsed_payload: Mapping[str, Any],
    source_format: str,
    validation_pipeline: ValidationPipeline | None,
    mode: str,
    stage_modes: Mapping[str, str] | None,
) -> ValidationResult:
    validators = (
        validation_pipeline
        or ValidationPipeline(
            validators=[
                SyntacticValidator(),
                StructuralValidator(),
            ]
        )
    ).validators
    issues = []
    executed_validators: list[str] = []
    effective_stage_modes: dict[str, str] = {}

    for validator in validators:
        # Syntactic validation requires serialized text; skip it for native mappings.
        if source_format == "native" and isinstance(
            validator, SyntacticValidator
        ):
            continue

        stage_pipeline = ValidationPipeline([validator])
        stage_target: str | Mapping[str, Any]
        if isinstance(validator, SyntacticValidator):
            stage_target = serialized_payload
        else:
            stage_target = parsed_payload

        # Always pass raise_on_error=False so every stage runs and aggregates its
        # issues. The callers (world_from_mapping / _world_from_serialized) decide
        # whether to raise based on the final combined result.
        stage_result = stage_pipeline.validate(
            stage_target,
            mode=mode,
            context=ValidationContext(
                metadata={"format": source_format}
            ),
            stage_modes=stage_modes,
            raise_on_error=False,
        )
        issues.extend(stage_result.issues)
        executed_validators.append(validator.name)
        effective_mode = (
            stage_modes.get(validator.name, mode)
            if stage_modes
            else mode
        )
        effective_stage_modes[validator.name] = effective_mode

    return ValidationResult(
        issues=issues,
        stage=(
            executed_validators[-1]
            if executed_validators
            else ""
        ),
        policy_mode=mode,
        metadata={
            "executed_validators": executed_validators,
            "effective_stage_modes": effective_stage_modes,
            "source_format": source_format,
        },
    )


def _coerce_text(payload: str | bytes) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, bytes):
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "Serialized world payload must be UTF-8 text"
            ) from exc
    raise ValueError(
        "Serialized world payload must be str or bytes"
    )


def _parse_world_payload(
    payload: str,
    format_hint: str,
) -> tuple[dict[str, Any], str]:
    normalized_format = str(format_hint).lower()
    if normalized_format not in SUPPORTED_WORLD_INPUT_FORMATS:
        raise ValueError(
            f"Unsupported world input format: {format_hint}"
        )

    if normalized_format == "json":
        parsed = _parse_json(payload)
        return _require_mapping_payload(parsed, "json"), "json"

    if normalized_format == "yaml":
        parsed = _parse_yaml(payload)
        return _require_mapping_payload(parsed, "yaml"), "yaml"

    json_error: ValueError | None = None
    try:
        return (
            _require_mapping_payload(
                _parse_json(payload), "json"
            ),
            "json",
        )
    except ValueError as exc:
        json_error = exc

    try:
        return (
            _require_mapping_payload(
                _parse_yaml(payload), "yaml"
            ),
            "yaml",
        )
    except ValueError as exc:
        raise ValueError(
            "Cannot parse world payload as JSON or YAML: "
            f"json={json_error}; yaml={exc}"
        ) from exc


def _parse_json(payload: str) -> Any:
    try:
        return json.loads(payload)
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc


def _parse_yaml(payload: str) -> Any:
    try:
        return yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise ValueError(str(exc)) from exc


def _require_mapping_payload(
    payload: Any, payload_format: str
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError(
            f"World {payload_format} payload must decode to a mapping, got "
            f"{type(payload).__name__}"
        )
    return dict(payload)
