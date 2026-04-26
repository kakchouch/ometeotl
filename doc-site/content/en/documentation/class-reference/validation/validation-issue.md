---
title: "ValidationIssue"
---

Source:
- [src/ometeotl_core/validation/base.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/base.py)

Local role:
Atomic validation finding with code, severity, message, and context.

Big-picture role:
Standardized issue contract shared by all validation stages and command boundary exports.

Inheritance:
- frozen dataclass

Parameters and fields:
- `code: str`
- `severity: str` (`error`, `warning`, `info`)
- `message: str`
- `object_id: str`
- `path: str`
- `suggestion: str`
- `context: JsonMap`
