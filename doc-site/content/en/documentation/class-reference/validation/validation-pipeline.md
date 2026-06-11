---
title: "ValidationPipeline"
---

Source:
- [src/ometeotl_core/validation/pipeline.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/pipeline.py)

Local role:
Orchestrates ordered validator execution and result aggregation.

Big-picture role:
Single staged entry point for validation policies across validation and core authority boundaries.

Key modes:
- `strict`
- `lenient`
- `warn_only`

Key behavior:
- per-stage mode overrides with `stage_modes`
- error downgrading in `warn_only`
- optional strict raising (`ValidationException`) when configured
- metadata for executed validators and effective stage modes

Example:

```python
from ometeotl_core.validation.pipeline import ValidationPipeline
from ometeotl_core.validation.base import ValidationContext

pipeline = ValidationPipeline(
    validators=[syntactic_validator, structural_validator],
    mode="strict",
    stage_modes={"syntactic": "warn_only"},
)
ctx = ValidationContext(
    stage="structure", policy_mode="strict",
    actor_id="actor-1", world_id="world-1", metadata={}
)
result = pipeline.validate(world, ctx)

if result.valid:
    print("All checks passed")
else:
    for issue in result.errors:
        print(issue.code, "-", issue.message)
```
