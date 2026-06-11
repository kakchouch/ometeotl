---
title: "ValidationContext"
---

Source:
- [src/ometeotl_core/validation/base.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/base.py)

Local role:
Execution context passed to each validator stage.

Big-picture role:
Carries policy mode plus actor/world/metadata payload needed by contextual validators.

Inheritance:
- frozen dataclass

Parameters and fields:
- `stage: str`
- `policy_mode: str`
- `actor_id: str`
- `world_id: str`
- `metadata: JsonMap`

Example:

```python
from ometeotl_core.validation.base import ValidationContext

ctx = ValidationContext(
    stage="structure",
    policy_mode="strict",
    actor_id="actor-1",
    world_id="world-1",
    metadata={"source": "import", "schema_version": "1.0"},
)
# Passed as-is to each validator stage in the pipeline
```
