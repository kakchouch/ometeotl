---
title: "GenerationRule / GenerationRuleSet / RuleRegistry"
---

Source:
- [src/ometeotl_core/generation/rule_engine.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generation/rule_engine.py)

__

Local role:
Pluggable, ordered transformation layer that refines a `GenerationContext` before it is handed to builders. All rules are deterministic: same input → same output, no side effects.

Big-picture role:
Implements the rule engine and constraint propagation requirements of F-17 and F-18. Consumed by [ContextualGenerationPipeline](/ometeotl/documentation/class-reference/generation/pipeline/). The `RuleRegistry` enables pluggable policy selection without modifying pipeline code.

Parameters and fields (`GenerationRule`, frozen dataclass):
- `name: str` — unique human-readable identifier
- `predicate: Callable[[GenerationContext], bool]` — guard; rule runs only when this returns `True`
- `apply: Callable[[GenerationContext], GenerationContext]` — pure transformation returning a new context

Methods (`GenerationRule`):
- `run(context)` — calls predicate; if `True` calls `apply` and returns result, otherwise returns context unchanged

Parameters and fields (`GenerationRuleSet`):
- `rules: list[GenerationRule]` — ordered rule list (property; returns a copy)

Methods (`GenerationRuleSet`):
- `apply(context)` — threads the context through each rule in order; returns the final context

Methods (`RuleRegistry`):
- `register(name, rule_set)` — stores a rule set under `name`; raises `ValueError` on empty name
- `exists(name) -> bool` — returns `True` if the name is registered
- `get(name) -> GenerationRuleSet | None` — returns the rule set or `None`
- `require(name) -> GenerationRuleSet` — returns the rule set; raises `KeyError` on missing name
- `names() -> list[str]` — sorted list of all registered names

Module-level helpers:
- `default_generation_rules()` — 2 rules: `normalize_relations`, `promote_label`
- `temporal_constraint_rules()` — 1 rule: propagates `constraints["temporal"]` into `metadata`
- `spatial_constraint_rules()` — 1 rule: propagates `constraints["spatial"]` into `metadata`
- `admissibility_constraint_rules()` — 1 rule: propagates `constraints["admissibility"]` into `metadata`
- `combined_generation_rules()` — all 5 rules in order; default for `ContextualGenerationPipeline`
- `default_rule_registry()` — pre-populated `RuleRegistry` with entries: `"default"`, `"temporal"`, `"spatial"`, `"admissibility"`, `"combined"`

Notes:
- All metadata propagation uses `setdefault` — existing metadata values are never overwritten by constraint rules.
- `rules.py` re-exports all symbols from `rule_engine.py` for backward compatibility.

See also:
- [GenerationContext](/ometeotl/documentation/class-reference/generation/generation-context/)
- [Pipeline](/ometeotl/documentation/class-reference/generation/pipeline/)

## Constraint propagation detail

### `temporal_constraint_rules` — fires when `constraints["temporal"]` is present

| Constraint key | Propagation target | Coercion |
|---|---|---|
| `window` | `metadata["horizon"]["window"]` | Positive int; fallback: `1` |
| `start_step` | `metadata["timeline"]["start_step"]` | Non-negative int; fallback: `0` |

### `spatial_constraint_rules` — fires when `constraints["spatial"]` is present

| Constraint key | Propagation target | Processing |
|---|---|---|
| `allowed_spaces` | `metadata["allowed_spaces"]` | Sorted, deduplicated list of non-empty strings |
| `required_space` | `metadata["space_id"]` | String coercion |

### `admissibility_constraint_rules` — fires when `constraints["admissibility"]` is present

| Constraint key | Propagation target | Processing |
|---|---|---|
| `required_capability` | `metadata["required_capability"]` | String coercion |
| `minimum_confidence` | `metadata["minimum_confidence"]` | Float clamped to `[0.0, 1.0]`; invalid → `0.0` |

## Constraint declaration pattern

```python
ctx = GenerationContext(
    kind="goal",
    id="goal-1",
    constraints={
        "temporal": {"window": 10, "start_step": 2},
        "spatial": {"allowed_spaces": ["north", "south"]},
        "admissibility": {"required_capability": "mobility", "minimum_confidence": 0.8},
    },
    metadata={"actor_id": "actor-1"},
)
pipeline = ContextualGenerationPipeline()  # uses combined rules by default
result = pipeline.generate(ctx)
```
