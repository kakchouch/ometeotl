---
title: "ProjectedPerceptionChange"
---

Source:
- [src/ometeotl_core/model/projection.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/projection.py)

Local role:
One explicit change applied while deriving a successor perceived state from an action projection.

Big-picture role:
Audit-friendly delta object that makes projected changes visible instead of hiding them inside the final projected perception only.

Inheritance:
- dataclass

Parameters and fields:
- change_id: str
- change_type: str
- subject_id: Optional[str]
- space_id: Optional[str]
- applied: Optional[bool]
- metadata: dict

Known `change_type` values:
- `state_changes`
- `resource_consume`
- `resource_produce`
- `object_added`
- `object_removed`
- `component_added`
- `component_removed`

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> ProjectedPerceptionChange`

Notes:
- `component_added` and `component_removed` describe projected changes to perceived actor composition, not mutations of the ontological world model.

See also:
- [ProjectedPerceptionState](/ometeotl/documentation/class-reference/model/projection/projected-perception-state/)
- [ActionProjection](/ometeotl/documentation/class-reference/model/projection/action-projection/)