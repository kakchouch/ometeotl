---
title: "PerceivedMembership"
---

Source:
- [src/ometeotl_core/model/perception.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/perception.py)

Local role:
Epistemic wrapper around one copied [SpaceObjectMembership](/ometeotl/documentation/class-reference/model/spaces/space-object-membership/).

Big-picture role:
Actor-specific placement knowledge item inside [Perception](/ometeotl/documentation/class-reference/model/perception/perception/).

Inheritance:
- dataclass

Parameters and fields:
- membership: [SpaceObjectMembership](/ometeotl/documentation/class-reference/model/spaces/space-object-membership/)
- `epistemic_status: str`
- `noise_metadata: JsonMap`

Methods:
- `to_dict(...)`
- `from_dict(...)`
- `__post_init__(...)`

See also:
- [PerceivedSpace](/ometeotl/documentation/class-reference/model/perception/perceived-space/)
