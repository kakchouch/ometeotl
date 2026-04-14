---
title: "ProjectionAssumption"
---

Source:
- [src/masm/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/projection.py)

Local role:
One explicit assumption extracted from evaluating an [Action](/ometeotl/documentation/class-reference/model/actions/action/) under a [Perception](/ometeotl/documentation/class-reference/model/perception/perception/) and a resource set.

Big-picture role:
Projection atom used to externalize the assumptions from which later strategy nodes may be built.

Inheritance:
- dataclass

Parameters and fields:
- assumption_id: str
- assumption_type: str
- description: str
- subject_id: Optional[str]
- epistemic_status: str
- satisfied: Optional[bool]
- rationale: str
- metadata: dict

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> ProjectionAssumption`

See also:
- [ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/)
- [ProjectionTool](/ometeotl/documentation/class-reference/model/projection/projection-tool/)