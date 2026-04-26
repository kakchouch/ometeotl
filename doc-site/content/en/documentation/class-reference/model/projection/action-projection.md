---
title: "ActionProjection"
---

Source:
- [src/ometeotl_core/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/projection.py)

Local role:
Serializable result of projecting one [Action](/ometeotl/documentation/class-reference/model/actions/action/) from one [Perception](/ometeotl/documentation/class-reference/model/perception/perception/) with an explicit resource set.

Big-picture role:
Intermediate projection artifact that records explicit assumptions and the projected successor perceived state before later strategy-node construction.

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
- projected_state: Optional[[ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)]
- metadata: dict

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> ActionProjection`

See also:
- [ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)
- [ProjectionBatch](/ometeotl/documentation/class-reference/model/projection/projection-batch/)
- [DefaultProjectionTool](/ometeotl/documentation/class-reference/model/projection/default-projection-tool/)