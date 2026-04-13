---
title: "ModelObject"
---

Source:
- [src/masm/model/base.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/base.py)

Local role:
Universal schema root for core model entities.

Big-picture role:
Canonical serialization backbone used by [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/), [Action](/ometeotl/documentation/class-reference/model/actions/action/), and all domain subclasses.

Inheritance:
- dataclass root

Parameters and fields:
- `id: ObjectId`
- `object_type: str`
- `schema_version: SchemaVersion`
- `attributes: JsonMap`
- `relations: RelationMap`
- `state: JsonMap`
- `context: JsonMap`
- `provenance: JsonMap`

Methods:
- mutation helpers: `set_mutation_guard`, `add_relation`, `remove_relation`, `_manage_relation`
- map/list helpers: `set_attribute`, `set_state`, `set_provenance`, `add_to_attribute_list`, `remove_from_attribute_list`
- serialization: `to_dict`, `from_dict`, `_base_kwargs`

See also:
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/)
- [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/)
