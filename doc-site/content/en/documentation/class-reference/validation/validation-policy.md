---
title: "Validation Policy Profiles"
---

Source:
- [src/masm/validation/policy.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/validation/policy.py)

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
