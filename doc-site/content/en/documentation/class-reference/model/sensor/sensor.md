---
title: "Sensor"
---

Source:
- [src/masm/model/sensor.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/sensor.py)

Local role:
Builds one [Perception](/ometeotl/documentation/class-reference/model/perception/perception/) for one actor from one [World](/ometeotl/documentation/class-reference/model/world/world/).

Big-picture role:
Bridge between ontology and epistemic state, composing [CoverageRule](/ometeotl/documentation/class-reference/model/sensor/coverage-rule/) and [NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/) policies.

Inheritance:
- dataclass

Parameters and fields:
- coverage_rules: List[[CoverageRule](/ometeotl/documentation/class-reference/model/sensor/coverage-rule/)]
- noise_rules: List[[NoiseRule](/ometeotl/documentation/class-reference/model/sensor/noise-rule/)]
- `default_epistemic_status: str`

Methods:
- sense(world, actor_id, timestamp=None) -> [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)
- internal passes: `_sense_spaces`, `_sense_memberships`, `_sense_relations`
- policy aggregators: `_covers_space`, `_covers_membership`, `_covers_relation`
- noise pipeline: `_apply_noise_to_space`, `_apply_noise_to_membership`, `_apply_noise_to_relation`, `_apply_noise`

See also:
- [PerceivedSpace](/ometeotl/documentation/class-reference/model/perception/perceived-space/)
- [PerceivedMembership](/ometeotl/documentation/class-reference/model/perception/perceived-membership/)
- [PerceivedRelation](/ometeotl/documentation/class-reference/model/perception/perceived-relation/)
