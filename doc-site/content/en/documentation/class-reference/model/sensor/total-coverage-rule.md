---
title: "TotalCoverageRule"
---

Source:
- [src/ometeotl_core/model/sensor.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/sensor.py)

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

Example:

```python
from ometeotl_core.model.sensor import Sensor, TotalCoverageRule, IdentityNoiseRule

# Fully transparent sensor — every space, membership, and relation is visible
sensor = Sensor(
    coverage_rules=[TotalCoverageRule()],
    noise_rules=[IdentityNoiseRule()],
    default_epistemic_status="certain",
)
perception = sensor.sense(world, actor_id="actor-1")
# perception includes all spaces and all memberships without filtering
```

See also:
- [IdentityNoiseRule](/ometeotl/documentation/class-reference/model/sensor/identity-noise-rule/)
