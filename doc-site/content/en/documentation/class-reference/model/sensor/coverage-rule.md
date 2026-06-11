---
title: "CoverageRule"
---

Source:
- [src/ometeotl_core/model/sensor.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/sensor.py)

Local role:
Abstract visibility policy.

Big-picture role:
Extensibility seam controlling which spaces, memberships, and relations enter [Perception](/ometeotl/documentation/class-reference/model/perception/perception/) through [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/).

Inheritance:
- abstract base class

Methods:
- `covers_space(space, actor_id, world) -> bool`
- `covers_membership(membership, actor_id, world) -> bool`
- `covers_relation(relation, actor_id, world) -> bool`

Example:

```python
from ometeotl_core.model.sensor import CoverageRule

class PhysicalOnlyCoverageRule(CoverageRule):
    """Only include physical spaces and their memberships/relations."""

    def covers_space(self, space, actor_id, world):
        return space.kind == "physical"

    def covers_membership(self, membership, actor_id, world):
        space = world.get_space(membership.space_id)
        return space is not None and space.kind == "physical"

    def covers_relation(self, relation, actor_id, world):
        return True
```

See also:
- [TotalCoverageRule](/ometeotl/documentation/class-reference/model/sensor/total-coverage-rule/)
- [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/)
