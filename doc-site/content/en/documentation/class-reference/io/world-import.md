---
title: "World import"
---

Source:
- [src/ometeotl_core/io/importers.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/io/importers.py)

Local role:
Validated reconstruction of a `World` from JSON text, YAML text, or an already-parsed mapping.

Big-picture role:
The import pipeline composes the existing `SyntacticValidator`, `StructuralValidator`, and `ValidationPipeline` from `ometeotl_core.validation` with `World.from_dict` from `ometeotl_core.model`. It keeps parse, validate, and reconstruct as separate internal steps so each failure mode is individually diagnosable. Business logic and serialization rules remain in `model`; validation rules remain in `validation`; IO only orchestrates.

## `WorldImportResult`

Frozen dataclass returned by every import helper.

| Field | Type | Description |
|---|---|---|
| `world` | `World` | Reconstructed world instance |
| `validation` | `ValidationResult` | Aggregated result from the staged pipeline |
| `payload` | `dict` | The parsed canonical mapping (plain dict) |
| `parsed_format` | `str` | `"json"`, `"yaml"`, or `"native"` |

## Public functions

### `world_from_mapping(payload, *, validation_pipeline, mode, stage_modes, raise_on_error)`

Accepts an already-parsed mapping. Skips syntactic parsing; runs structural validation on the native payload. Default `mode` is `strict`.

### `world_from_json(payload, *, ...)`

Accepts a JSON `str` or `bytes`. Runs syntactic validation on the raw text, structural validation on the parsed mapping, then reconstructs.

### `world_from_yaml(payload, *, ...)`

Accepts a YAML `str` or `bytes`. Same pipeline as JSON, with `format_hint="yaml"`.

### `read_world_json(path, *, ...)`

Reads UTF-8 JSON from a file path, then delegates to `world_from_json`.

### `read_world_yaml(path, *, ...)`

Reads UTF-8 YAML from a file path, then delegates to `world_from_yaml`.

## Validation pipeline details

The default pipeline runs two staged validators in order:

1. **syntactic** — receives the raw serialized text (or the native mapping for `world_from_mapping`). Checks JSON/YAML parseability and format.
2. **structural** — receives the parsed mapping. Checks required fields, field types, and schema version.

You can supply a custom `ValidationPipeline` to override this default. Additional domain validators (temporal, spatial, epistemic, etc.) can be added to that pipeline. Stage-level mode overrides are forwarded from the `stage_modes` parameter.

## Failure contract

- Parse errors raise `ValueError` before any validation runs.
- Validation failures with `raise_on_error=True` (the default) raise `ValidationException` carrying the full `ValidationResult`.
- Automatic repair is not performed; diagnostics must be acted on by the caller.
- Deferred phases: LLM-view export, schema-backed validation, and automated repair are excluded from V1.
