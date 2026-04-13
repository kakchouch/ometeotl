---
title: "NoiseRule"
---

Source:
- [src/masm/model/sensor.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/sensor.py)

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

See also:
- [IdentityNoiseRule](/ometeotl/documentation/class-reference/model/sensor/identity-noise-rule/)
