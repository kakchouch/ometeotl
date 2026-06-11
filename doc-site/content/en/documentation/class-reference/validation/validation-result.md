---
title: "ValidationResult"
---

Source:
- [src/ometeotl_core/validation/base.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/base.py)

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

Example:

```python
result = pipeline.validate(world, context)

print(result.valid)              # False if any error present
print(result.summary)            # human-readable summary string
print(len(result.errors))
print(len(result.warnings))

# Merge two stage results into one combined report
combined = result_stage1.merged_with(result_stage2)
```
