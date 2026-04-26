---
title: "ProjectionBatch"
---

Source:
- [src/ometeotl_core/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/projection.py)

Local role:
Deterministic batch of [ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/) instances for one actor/perception context.

Big-picture role:
Batch transport object for first-order projection over a candidate action set.

Inheritance:
- dataclass

Parameters and fields:
- actor_id: str
- source_perception_id: str
- source_id: str
- projections: list[[ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/)]
- metadata: dict

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> ProjectionBatch`

See also:
- [ProjectionTool](/ometeotl/documentation/class-reference/model/projection/projection-tool/)