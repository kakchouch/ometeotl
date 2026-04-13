---
title: "PerceivedSpace"
---

Source:
- [src/masm/model/perception.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/perception.py)

Local role:
Epistemic wrapper around one copied [Space](/ometeotl/documentation/class-reference/model/spaces/space/).

Big-picture role:
Captures actor-relative certainty and noise metadata in [Perception](/ometeotl/documentation/class-reference/model/perception/perception/).

Inheritance:
- dataclass

Parameters and fields:
- space: [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
- `epistemic_status: str`
- `noise_metadata: JsonMap`

Methods:
- `to_dict(...)`
- `from_dict(...)`
- `__post_init__(...)`

See also:
- [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/)
