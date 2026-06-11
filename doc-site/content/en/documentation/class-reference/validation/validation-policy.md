---
title: "Validation Policy Profiles"
---

Source:
- [src/ometeotl_core/validation/policy.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/policy.py)

Local role:
Maps high-level hardening profiles to per-stage pipeline modes.

Available profiles:
- `observe_only`
- `enforce_structure`
- `enforce_domain`

Entry point:
- `build_stage_modes(...)`

Big-picture role:
Progressive hardening control used by `AuthorityCommandHandler` and `build_runtime(...)`.

Example:

```python
from ometeotl_core.validation.policy import build_stage_modes
from ometeotl_core.generic.authority import AuthorityCommandHandler

# Obtain per-stage modes for a named profile
stage_modes = build_stage_modes("enforce_domain")

# Apply via AuthorityCommandHandler
handler = AuthorityCommandHandler(
    world=world,
    validation_policy_profile="enforce_domain",
    validation_soft_gate=True,
    validation_block_on_error=True,
)
```
