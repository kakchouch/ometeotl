---
title: "IdentityNoiseRule"
---

Source:
- [src/ometeotl_core/model/sensor.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/sensor.py)

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

Example:

```python
from ometeotl_core.model.sensor import Sensor, TotalCoverageRule, IdentityNoiseRule

# Zero-noise baseline: copies are returned unmodified
# Useful to isolate coverage behavior without distortion side-effects
sensor = Sensor(
    coverage_rules=[TotalCoverageRule()],
    noise_rules=[IdentityNoiseRule()],
    default_epistemic_status="certain",
)
perception = sensor.sense(world, actor_id="actor-1")
```

See also:
- [TotalCoverageRule](/ometeotl/documentation/class-reference/model/sensor/total-coverage-rule/)
