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
