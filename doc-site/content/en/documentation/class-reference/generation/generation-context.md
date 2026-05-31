---
title: "GenerationContext / GenerationPlacement"
---

Source:
- [src/ometeotl_core/generation/context.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generation/context.py)

__

Local role:
Declarative input dataclass threaded through every generation function and builder. Carries identity, attributes, nested child contexts, placement instructions, and optional constraint overrides.

Big-picture role:
Central data-transfer object of the generation pipeline (F-16 to F-22). Consumed by [ContextualBuilder](/ometeotl/documentation/class-reference/generation/context-builder/), the [rule engine](/ometeotl/documentation/class-reference/generation/rule-engine/), and [ContextualGenerationPipeline](/ometeotl/documentation/class-reference/generation/pipeline/).

Parameters and fields (`GenerationContext`):
- `kind: str` — target entity kind: `"world"`, `"actor"`, `"goal"`, `"strategy"`, `"perception"`, `"space"`, `"resource"`, `"action"`
- `id: str` — stable identity of the generated object
- `label: str` — promoted into `attributes["label"]` by the `promote_label` rule
- `attributes: dict` — arbitrary key/value pairs forwarded to the model object
- `relations: dict[str, list[str]]` — named relation groups; duplicates deduplicated by `normalize_relations`
- `state: dict`, `context: dict`, `provenance: dict` — forwarded verbatim to the model object
- `spaces`, `actors`, `resources`, `goals`, `strategies`, `actions: list[GenerationContext]` — nested child contexts for world generation
- `placements: list[GenerationPlacement]` — explicit object-to-space placement instructions
- `metadata: dict` — read by constraint propagation rules; also forwarded into `merged_context()`
- `rules: dict` — rule override hints (reserved)
- `constraints: dict` — constraint declarations consumed by the [rule engine](/ometeotl/documentation/class-reference/generation/rule-engine/)
- `operation: str` — `"create"` (default), `"partial_update"`, `"corrective_update"`
- `registration_policy: str` — `"none"` (default), `"if_available"`, `"require"`
- `validate: bool` — if `True`, pipeline runs validation after generation
- `validation_mode: str` — `"lenient"` (default) or `"strict"`
- `stage_modes: dict[str, str]` — per-stage validation mode overrides

Methods:
- `merged_attributes()` — attributes with `label` promoted when non-empty
- `merged_context()` — ambient context enriched with `metadata`, `rules`, `constraints` under a `"generation"` key
- `normalized_relations()` — relations with each list deduplicated and sorted
- `copy_with(**overrides)` — shallow copy with field overrides; used by the rule engine on every rule application
- `child_collections()` — all nested child context lists in one stable mapping

Parameters and fields (`GenerationPlacement`):
- `object_id: str` — ID of the object to place
- `space_id: str` — ID of the target space
- `role: str = "occupies"` — semantic role of the placement
- `metadata: dict = {}` — optional placement metadata

Methods (`GenerationPlacement`):
- `to_dict()` — returns a plain dict representation

Notes:
- `GenerationContext` is mutable; all fields default so callers only set what they need.
- `GenerationPlacement` is a frozen dataclass.
- `copy_with` is the only intended mutation path inside the rule engine — direct field mutation should be avoided.
- `constraints` keys `"temporal"`, `"spatial"`, `"admissibility"` are the conventionally recognized namespaces.

See also:
- [Rule engine](/ometeotl/documentation/class-reference/generation/rule-engine/)
- [ContextualBuilder](/ometeotl/documentation/class-reference/generation/context-builder/)
- [Pipeline](/ometeotl/documentation/class-reference/generation/pipeline/)
