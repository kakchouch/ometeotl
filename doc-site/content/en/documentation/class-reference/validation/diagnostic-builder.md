---
title: "DiagnosticBuilder"
---

Source:
- [src/ometeotl_core/validation/diagnostic.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/diagnostic.py)

Local role:
Builds user-facing diagnostics from `ValidationResult`.

Big-picture role:
Implements motivated rejection support and repair-ready issue suggestions.

Outputs:
- `DiagnosticEntry`
- `DiagnosticReport`

Example:

```python
from ometeotl_core.validation.diagnostic import DiagnosticBuilder

builder = DiagnosticBuilder()
report = builder.build(validation_result)

for entry in report.entries:
    print(f"[{entry.severity}] {entry.code}: {entry.message}")
    if entry.suggestion:
        print(f"  → {entry.suggestion}")
```
