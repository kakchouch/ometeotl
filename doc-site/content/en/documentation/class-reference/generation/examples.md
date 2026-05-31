---
title: "Generation examples"
---

Source:
- [src/ometeotl_core/generation/examples.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generation/examples.py)

__

Local role:
Self-contained runnable demo scenarios for the contextual generation pipeline. Each function is independent and illustrates one generation pattern end to end.

Big-picture role:
Executable documentation for the generation architecture (F-16 to F-22). Run `python -m ometeotl_core.generation.examples` to see all four scenarios.

Module-level helpers:
- `demo_simple_world()` — generates a world with 2 spaces and 1 placed actor; demonstrates nested contexts and `GenerationPlacement`
- `demo_multi_actor_world()` — generates a world with 3 actors and temporal/spatial constraint propagation; demonstrates deduplication and `combined_generation_rules`
- `demo_perception_generation()` — generates a `Perception` object for an actor observing a known space; demonstrates metadata-driven perception and registry-selected rule sets
- `demo_goal_generation()` — generates a `Goal` with admissibility constraints; demonstrates confidence clamping, capability propagation, and priority validation
- `run_all()` — runs all four scenarios in sequence; called when the module is executed directly

Notes:
- All scenarios use `ContextualGenerationPipeline` with no custom configuration unless stated.
- `demo_perception_generation` selects the `"default"` rule set from `default_rule_registry()` to demonstrate registry-driven rule selection.
- `Goal.priority` must be in `[0.0, 1.0]` — see [Goal](/ometeotl/documentation/class-reference/model/goals/goal/).

See also:
- [GenerationContext](/ometeotl/documentation/class-reference/generation/generation-context/)
- [Pipeline](/ometeotl/documentation/class-reference/generation/pipeline/)
- [Rule engine](/ometeotl/documentation/class-reference/generation/rule-engine/)
