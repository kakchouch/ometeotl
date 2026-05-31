---
title: "ContextualBuilder / per-kind builders"
---

Source:
- [src/ometeotl_core/generation/context_builder.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generation/context_builder.py)

__

Local role:
Typed class-based abstraction wrapping the function-based builders in `builders.py`. Provides a stable override point for kind-specific generation behavior.

Big-picture role:
Enables callers to compose or replace per-kind generation logic without touching the pipeline. Satisfies the pluggable builder requirement of the generation architecture (F-16).

Inheritance (`ContextualBuilder`):
- `ABC`, `Generic[TGenerated]`

Parameters and fields:
- `kind: str` — class-level attribute; must be declared on each concrete subclass

Methods (`ContextualBuilder`):
- `ensure_kind(context)` — raises `ValueError` if `context.kind` does not match `self.kind`
- `build(context) -> TGenerated` — abstract; must be implemented by subclasses

Concrete builders:
- `WorldContextualBuilder` — `kind = "world"`, delegates to `build_world(context)`
- `ActorContextualBuilder` — `kind = "actor"`, delegates to `build_actor(context)`
- `StrategyContextualBuilder` — `kind = "strategy"`, delegates to `build_strategy(context)`
- `GoalContextualBuilder` — `kind = "goal"`, delegates to `build_goal(context)`
- `PerceptionContextualBuilder` — `kind = "perception"`, delegates to `build_perception(context)`

Module-level helpers:
- `default_contextual_builders()` — returns a `dict[str, ContextualBuilder]` mapping all five built-in kind strings to their instances
- `build_with_context_builder(context, *, builders=None)` — looks up `context.kind` in the builders dict and calls `build(context)`; raises `ValueError` on unknown kind

Notes:
- Every concrete `build()` implementation must call `ensure_kind` first to prevent silent wrong-kind generation.
- `default_contextual_builders()` returns a fresh dict each call — safe to mutate.

See also:
- [GenerationContext](/ometeotl/documentation/class-reference/generation/generation-context/)
- [Pipeline](/ometeotl/documentation/class-reference/generation/pipeline/)

## Customization pattern

```python
class MyActorBuilder(ActorContextualBuilder):
    def build(self, context):
        self.ensure_kind(context)
        ctx = context.copy_with(attributes={**context.attributes, "source": "custom"})
        return build_actor(ctx)

builders = default_contextual_builders()
builders["actor"] = MyActorBuilder()
result = build_with_context_builder(context, builders=builders)
```
