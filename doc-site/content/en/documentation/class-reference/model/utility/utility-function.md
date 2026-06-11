---
title: "UtilityFunction"
---

Source:
- [src/ometeotl_core/model/utility.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/utility.py)

Local role:
Abstract utility interface required by the model layer.

Big-picture role:
Domain-neutral contract defining how actor-relative perceived states are scored under an interpretive framework.

Inheritance:
- abstract base class

Core contract:
- `framework_id` property
- `is_multi_criteria` property
- `evaluate(perception, actor, context) -> UtilityFrame`

Helper behavior:
- deterministic missing-metric resolution policies
- standardized UtilityFrame construction helpers

Concrete game-layer implementations:
- [WeightedSumUtility](/ometeotl/documentation/class-reference/game/utility/weighted-sum-utility/)
- [LexicographicUtility](/ometeotl/documentation/class-reference/game/utility/lexicographic-utility/)

Example:

```python
from ometeotl_core.model.utility import UtilityFunction, UtilityFrame

class ResourceScoreUtility(UtilityFunction):
    """Score an actor by the number of resources they hold."""

    @property
    def framework_id(self):
        return "resource_score"

    @property
    def is_multi_criteria(self):
        return False

    def evaluate(self, perception, actor, context):
        count = len(perception.memberships_for_object(actor.id))
        return UtilityFrame(value=float(count), framework_id=self.framework_id)
```