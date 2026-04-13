---
title: "IdentityNoiseRule"
---

Source:
- [src/masm/model/sensor.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/sensor.py)

Local role:
Default [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/) that leaves copies unchanged.

Big-picture role:
Zero-noise baseline to isolate coverage behavior in [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/).

Inheritance:
- [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/)

Methods:
- `apply_to_space(...)`
- `apply_to_membership(...)`
- `apply_to_relation(...)`

See also:
- [TotalCoverageRule](/ometeotl/documentation/class-reference/model/sensor/total-coverage-rule/)
