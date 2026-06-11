---
title: "LLM view export"
---

Source:
- [src/ometeotl_core/io/llm_export.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/io/llm_export.py)
- [src/ometeotl_core/model/base.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/base.py)

Local role:
Provide a language-model-oriented representation that explicitly separates ontological reality from epistemic/perception-aware views.

Big-picture role:
This export path implements the dedicated LLM/SLM view requirement (F-5) while preserving ownership boundaries:
- `model` owns canonical state (`to_dict` and domain classes)
- `io` owns formatting/projection for external consumers

## Public API

### `world_to_llm_view(world, include_provenance=False)`
Exports a world-focused LLM payload with:
- base object shape (`id`, `type`, optional sections)
- `reality` block
- member summaries and deterministic member lists

### `actor_to_llm_view(actor, perception=None, include_provenance=False)`
Exports an actor with:
- ontological actor slice
- optional attached perception view
- explicit epistemic envelope

### `perception_to_llm_view(perception, include_provenance=False)`
Exports a perception object with:
- perception payload (`perceived_spaces`, memberships, relations, component links)
- grouped epistemic statuses (`certain`, `believed`, `hypothesis`, `projected`, `error`)

### `ModelObject.to_llm_view()`
Shared model-level entrypoint dispatching to `LLMViewBuilder` by object type. Unsupported object types use a generic fallback containing `reality`, `perception`, and `epistemic` sections.

## Determinism and epistemic guarantees

- Perception payload collections are sorted with canonical keys.
- Epistemic status groups are produced deterministically.
- World member IDs (`actors`, `spaces`, `resources`) are sorted.
- Output explicitly exposes distinctions: `reality`, `perception`, `belief`, `hypothesis`, `projection`.

## Validation and scope

- This exporter does not run validation.
- It assumes input objects are already structurally valid.
- It is a projection layer, not a business-logic layer.

Example:

```python
from ometeotl_core.io.llm_export import (
    world_to_llm_view,
    actor_to_llm_view,
    perception_to_llm_view,
)

# World view: reality block + sorted member id lists
world_view = world_to_llm_view(world)
print(world_view["reality"]["actors"])

# Actor view with attached perception
actor_view = actor_to_llm_view(actor, perception=perception)
print(actor_view["epistemic"])

# Perception view: grouped by epistemic status
perc_view = perception_to_llm_view(perception)
print(perc_view["certain"])
print(perc_view["believed"])

# Via model object shortcut
llm_view = actor.to_llm_view()
```
