---
title: "ValidationResult"
---

Source:
- [src/masm/validation/base.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/validation/base.py)

Local role:
Aggregated result of one validator stage or full pipeline execution.

Big-picture role:
Stable structured contract consumed by diagnostics and authority command decisions.

Inheritance:
- dataclass

Parameters and fields:
- `issues: list[ValidationIssue]`
- `stage: str`
- `policy_mode: str`
- `metadata: JsonMap`

Derived helpers:
- `summary`
- `valid`
- `errors`
- `warnings`
- `infos`
- `merged_with(...)`
