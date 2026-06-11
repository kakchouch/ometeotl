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

Example:

```python
from ometeotl_core.validation.base import ValidationIssue

issue = ValidationIssue(
    code="MISSING_FIELD",
    severity="error",
    message="Required field 'actor_id' is missing on action-1",
    object_id="action-1",
    path="action.actor_id",
    suggestion="Set actor_id to a valid registered actor identifier",
    context={"object_type": "action"},
)
print(issue.severity)   # "error"
print(issue.code)       # "MISSING_FIELD"
```
