---
title: "CoverageRule"
---

Source:
- [src/masm/model/sensor.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/sensor.py)

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

See also:
- [TotalCoverageRule](/ometeotl/documentation/class-reference/model/sensor/total-coverage-rule/)
- [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/)
