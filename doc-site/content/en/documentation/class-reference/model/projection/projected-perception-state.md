---
title: "ProjectedPerceptionState"
---

Source:
- [src/masm/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/projection.py)

Local role:
Projected successor perceived state produced by evaluating one [Action](/ometeotl/documentation/class-reference/model/actions/action/) from one source [Perception](/ometeotl/documentation/class-reference/model/perception/perception/).

Big-picture role:
Bridge object between first-order projection and later strategy construction: it is the state that child strategy nodes consume.

Inheritance:
- dataclass

Parameters and fields:
- source_perception_id: str
- generating_action_id: str
- perception: [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)
- changes: list[[ProjectedPerceptionChange](/ometeotl/documentation/class-reference/model/projection/projected-perception-change/)]
- metadata: dict

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> ProjectedPerceptionState`

See also:
- [ProjectedPerceptionChange](/ometeotl/documentation/class-reference/model/projection/projected-perception-change/)
- [ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/)