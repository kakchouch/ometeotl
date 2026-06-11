---
title: "ContextualGenerationPipeline / GenerationResult"
---

Source:
- [src/ometeotl_core/generation/pipeline.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generation/pipeline.py)

__

Local role:
Orchestrates the full generation workflow: rule application → builder dispatch → optional registration → optional validation → structured result.

Big-picture role:
Top-level entry point for the generation architecture (F-16 to F-22). Accepts a `GenerationContext`, applies the configured `GenerationRuleSet`, delegates to the appropriate builder, and returns a `GenerationResult` carrying the generated object, applied rule names, validation outcome, and repair suggestions.

Parameters and fields (`ContextualGenerationPipeline`):
- `rules: GenerationRuleSet` — rule set applied before building; defaults to `combined_generation_rules()`
- `validation_pipeline: ValidationPipeline | None` — optional validation pipeline; only runs when `context.validate=True`

Methods (`ContextualGenerationPipeline`):
- `generate(context, *, world=None) -> GenerationResult` — full pipeline: rules → build → register → validate
- `generate_from_text_response(context, *, raw_response, ...)` — parses an LLM text response into context overrides then delegates to `generate`

Parameters and fields (`GenerationResult`, dataclass):
- `generated: Any` — the model object produced by the builder
- `applied_rule_names: list[str]` — names of rules that were part of the active rule set (in order)
- `validation: ValidationResult | None` — validation outcome; `None` if validation was not requested
- `diagnostics: list[str]` — ordered human-readable pipeline stage messages
- `uncertainty_zones: list[str]` — uncertainty zones declared in the context
- `repair_suggestions: list[str]` — suggested fixes when validation fails

Notes:
- Supported `context.operation` values: `"create"`, `"partial_update"`, `"corrective_update"`.
- Supported `context.registration_policy` values: `"none"`, `"if_available"`, `"require"`.
- `applied_rule_names` reflects the rule set configuration, not which predicates fired.
- Validation only runs when `context.validate=True` **and** a `validation_pipeline` is provided.
- The pipeline does not call `LLMGenerationAdapter` automatically; callers must chain it explicitly.

See also:
- [GenerationContext](/ometeotl/documentation/class-reference/generation/generation-context/)
- [Rule engine](/ometeotl/documentation/class-reference/generation/rule-engine/)
- [LLMGenerationAdapter](/ometeotl/documentation/class-reference/generation/llm-integration/)
- [Generation examples](/ometeotl/documentation/class-reference/generation/examples/)

Example:

```python
from ometeotl_core.generation.pipeline import ContextualGenerationPipeline
from ometeotl_core.generation.context import GenerationContext

ctx = GenerationContext(
    kind="actor",
    id="actor-1",
    label="Scout",
    attributes={"mobility": True},
    validate=True,
    validation_mode="lenient",
)

pipeline = ContextualGenerationPipeline()
result = pipeline.generate(ctx, world=world)

actor = result.generated
print(type(actor).__name__)           # "Actor"
print(result.applied_rule_names)      # rules that ran in the rule set
if result.validation:
    print(result.validation.valid)
```

## Generation flow

```
GenerationContext
    → GenerationRuleSet.apply()        # constraint propagation and normalization
    → build_from_context()             # kind dispatch → builder
    → registration_policy check        # optional world registry update
    → ValidationPipeline.validate()    # optional; only when context.validate=True
    → GenerationResult
```
