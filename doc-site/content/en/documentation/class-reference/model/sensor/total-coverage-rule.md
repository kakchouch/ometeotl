---
title: "TotalCoverageRule"
---

Source:
- [src/masm/model/sensor.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/sensor.py)

Local role:
Default [CoverageRule](/ometeotl/documentation/class-reference/model/sensor/coverage-rule/) that includes everything.

Big-picture role:
Transparent sensing baseline, useful as omniscient reference behavior for [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/).

Inheritance:
- [CoverageRule](/ometeotl/documentation/class-reference/model/sensor/coverage-rule/)

Methods:
- `covers_space(...) -> bool`
- `covers_membership(...) -> bool`
- `covers_relation(...) -> bool`

See also:
- [IdentityNoiseRule](/ometeotl/documentation/class-reference/model/sensor/identity-noise-rule/)
