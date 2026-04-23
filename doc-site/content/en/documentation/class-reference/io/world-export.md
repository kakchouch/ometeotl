---
title: "World export"
---

Source:
- [src/masm/io/exporters.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/io/exporters.py)

Local role:
Canonical JSON and YAML serialization of a `World` instance.

Big-picture role:
The IO export layer is a thin orchestration wrapper. It calls `World.to_dict()` for the canonical payload, normalizes all guarded container subclasses to plain Python dicts and lists via `_deep_plain_copy`, then formats the result to the requested text format. This keeps serialization ownership in `model` and format ownership in `io`.

## Public functions

### `world_to_mapping(world)`

Returns the canonical plain-dict payload for a world.
Uses `_deep_plain_copy` to strip guarded subclasses before returning, so the result is safe to pass to any serializer.

### `world_to_json(world, *, indent=2)`

Returns a deterministic JSON string.
Key ordering is always sorted. UTF-8 text output.

### `world_to_yaml(world)`

Returns a deterministic YAML string.
YAML is a secondary projection of the same canonical payload returned by `world_to_mapping`. It is not an independent serialization path.

### `write_world_json(world, path, *, indent=2)`

Writes JSON to a file. Returns the resolved `Path` object.

### `write_world_yaml(world, path)`

Writes YAML to a file. Returns the resolved `Path` object.

## Key constraints

- JSON is the canonical reference format (F-2).
- YAML is always derived from the same mapping as JSON; the two formats must encode the same payload.
- Exports are deterministic: same world always produces the same byte sequence (F-6).
- The exporter does not validate: call the import pipeline if validation is needed on re-import.
