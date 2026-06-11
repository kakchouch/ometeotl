---
title: "NoiseRule"
---

Source:
- [src/ometeotl_core/model/sensor.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/sensor.py)

Local role:
Abstract distortion policy over sensed copies.

Big-picture role:
Extensibility seam that injects uncertainty and bias into [Perception](/ometeotl/documentation/class-reference/model/perception/perception/) built by [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/).

Inheritance:
- abstract base class

Methods:
- apply_to_space(space, actor_id) -> Tuple[[Space](/ometeotl/documentation/class-reference/model/spaces/space/), JsonMap]
- apply_to_membership(membership, actor_id) -> Tuple[[SpaceObjectMembership](/ometeotl/documentation/class-reference/model/spaces/space-object-membership/), JsonMap]
- apply_to_relation(relation, actor_id) -> Tuple[[SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/), JsonMap]

Example:

```python
import copy
from ometeotl_core.model.sensor import NoiseRule

class LabelObfuscationRule(NoiseRule):
    """Replaces space labels with '???' to model imperfect identification."""

    def apply_to_space(self, space, actor_id):
        s = copy.deepcopy(space)
        s.set_attribute("label", "???")
        return s, {"obfuscated": True}

    def apply_to_membership(self, membership, actor_id):
        return membership, {}

    def apply_to_relation(self, relation, actor_id):
        return relation, {}
```

See also:
- [IdentityNoiseRule](/ometeotl/documentation/class-reference/model/sensor/identity-noise-rule/)
