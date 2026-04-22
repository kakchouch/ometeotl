---
title: "GoalBuildStep"
---

Source:
- [src/masm/model/goals.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/goals.py)

Local role:
Recursive declarative node used to build goal hierarchies.

Big-picture role:
Input specification for hierarchy builders that construct [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) trees without introducing domain-specific teleology.

Inheritance:
- dataclass

Fields:
- kind: str (`final` or `intermediate`)
- actor_id: str
- target_condition: dict
- horizon: dict
- priority: float
- status: str
- children: list[[GoalBuildStep](/ometeotl/documentation/class-reference/model/goals/goal-build-step/)]
- metadata: dict

See also:
- [Goal](/ometeotl/documentation/class-reference/model/goals/goal/)
- [GoalDecompositionTree](/ometeotl/documentation/class-reference/model/goals/goal-decomposition-tree/)