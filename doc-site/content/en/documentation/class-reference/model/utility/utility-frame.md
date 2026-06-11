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

Example:

```python
from ometeotl_core.model.utility import UtilityFrame

# Scalar frame
frame = UtilityFrame(
    value=0.85,
    framework_id="weighted_sum",
    criteria_labels=[],
    metadata={"source": "game-layer"},
)
print(frame.scalar_value)       # 0.85
print(frame.is_multi_criteria)  # False

# Multi-criteria frame (lexicographic)
multi = UtilityFrame(
    value=[0.9, 0.5],
    framework_id="lexicographic",
    criteria_labels=["safety", "speed"],
)
print(multi.is_multi_criteria)  # True

data = frame.to_dict()
frame2 = UtilityFrame.from_dict(data)
```

See also:
- [UtilityFunction](/ometeotl/documentation/class-reference/model/utility/utility-function/)