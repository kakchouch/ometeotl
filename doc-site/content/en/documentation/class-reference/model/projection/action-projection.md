---
title: "ActionProjection"
---

Source:
- [src/masm/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/projection.py)

Local role:
Serializable result of projecting one [Action](/ometeotl/documentation/class-reference/model/actions/action/) from one [Perception](/ometeotl/documentation/class-reference/model/perception/perception/) with an explicit resource set.

Big-picture role:
Intermediate projection artifact that records explicit assumptions before any strategy-node construction or branching logic.

Inheritance:
- dataclass

Parameters and fields:
- action_id: str
- actor_id: str
- source_perception_id: str
- source_id: str
- status: str
- resource_ids: list[str]
- assumptions: list[[ProjectionAssumption](/ometeotl/documentation/class-reference/model/projection/projection-assumption/)]
- metadata: dict

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> ActionProjection`

See also:
- [ProjectionBatch](/ometeotl/documentation/class-reference/model/projection/projection-batch/)
- [DefaultProjectionTool](/ometeotl/documentation/class-reference/model/projection/default-projection-tool/)