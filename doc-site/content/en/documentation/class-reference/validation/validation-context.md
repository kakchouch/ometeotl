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
