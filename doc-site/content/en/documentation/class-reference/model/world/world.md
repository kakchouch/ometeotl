---
title: "World"
---

Source:
- [src/masm/model/world.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/world.py)

Local role:
Root simulation container and orchestration hub.

Big-picture role:
Aggregates [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/), [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/), and [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/), while enabling authority mode used by [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/).

Inheritance:
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/)
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- `object_type: str = "world"`
- `is_root_world: bool`
- space_object_graph: [SpaceObjectGraph](/ometeotl/documentation/class-reference/model/spaces/space-object-graph/)
- space_relation_graph: [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/)
- model_registry: [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/)

Methods:
- authority mode: `enable_authority_mode`, `disable_authority_mode`
- topology operations: `add_space`, `add_space_relation`, `place_object`, `get_space`
- registry operations: `register_object`, `unregister_object`
- serialization: `to_dict`, `from_dict`

See also:
- [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/)
