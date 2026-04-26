---
title: "UtilityFrame"
---

Source:
- [src/ometeotl_core/model/utility.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/utility.py)

Local role:
Typed wrapper for scalar or vector utility evaluation results.

Big-picture role:
Standard utility payload shared by model-level utility contracts and game-level rankers.

Inheritance:
- dataclass

Fields:
- value: float or list[float]
- framework_id: str
- criteria_labels: list[str]
- metadata: dict

Methods:
- `to_dict() -> dict`
- `from_dict(data) -> UtilityFrame`

Properties:
- `is_multi_criteria`
- `scalar_value`

See also:
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/)