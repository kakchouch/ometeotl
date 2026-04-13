---
title: "SpaceRelationType"
---

Source:
- [src/masm/model/space_relations.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/model/space_relations.py)

Local role:
Metadata definition for one relation type.

Big-picture role:
Rule descriptor consumed by [SpaceRelation](/ometeotl/documentation/class-reference/model/space-relations/space-relation/) and [SpaceRelationGraph](/ometeotl/documentation/class-reference/model/space-relations/space-relation-graph/).

Inheritance:
- frozen dataclass

Parameters and fields:
- `name: str`
- `is_symmetric: bool`
- `is_antisymmetric: bool`
- `is_transitive: bool`
- `is_reflexive: bool`

Methods:
- no custom methods

See also:
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
