---
title: "Actor"
---

Source:
- [src/ometeotl_core/model/actors.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/actors.py)

Local role:
Represents an actor entity with roles, composition mode, and domain relations.

Big-picture role:
Central decision-capable abstraction consumed by [Action](/ometeotl/documentation/class-reference/model/actions/action/) and observed through [Sensor](/ometeotl/documentation/class-reference/model/sensor/sensor/).

Inheritance:
- [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/)
- [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/)

Parameters and fields:
- `object_type: str = "actor"`
- actor attributes: `kind`, `roles`, `emergent`, `composition_mode`
- composition modes: `standalone`, `composite`, `collective`, `perceived`, `projected`
- component relations are stored in `relations["component"]`

Methods:
- actor properties: `kind`, `roles`, `emergent`, `composition_mode`, `is_composite`, `is_collective`
- role methods: `add_role`, `remove_role`
- component methods: `get_components`, `add_component`, `remove_component`
- generated relation methods: `add_action/remove_action`, `add_resource/remove_resource`, `add_goal/remove_goal`, and related pairs
- `from_dict(...)`

Module-level helpers:
- `detect_composition_cycle(...)` checks whether adding a component would create a cycle
- `resolve_component_tree(...)` materializes a nested component hierarchy
- `find_parent_composites(...)` finds reverse component links
- `is_abstract_composite(...)` identifies a composite actor used as an abstraction node
- `get_concrete_components(...)` returns direct non-abstract components
- `get_real_world_base(...)` resolves the non-abstract leaves beneath an abstract hierarchy

Notes:
- Only actors in `composition_mode == "composite"` may carry explicit component links.
- `collective` actors model a coherent whole without explicit component relations.
- Composite actors support hierarchical nesting, while cycle creation is intentionally guarded by helper logic rather than being applied implicitly by `add_component(...)`.

Example:

```python
from ometeotl_core.model.actors import Actor, detect_composition_cycle

# Standalone actor with a role
actor = Actor(id="actor-1")
actor.add_role("scout")
actor.set_attribute("label", "Scout Alpha")

# Composite actor that groups components
composite = Actor(id="team-1", composition_mode="composite")
if not detect_composition_cycle(composite, "actor-1", registry):
    composite.add_component("actor-1")

print(composite.is_composite)   # True
print(composite.get_components())
```

See also:
- [Resource](/ometeotl/documentation/class-reference/model/resources/resource/)
- [Perception](/ometeotl/documentation/class-reference/model/perception/perception/)
- [Space](/ometeotl/documentation/class-reference/model/spaces/space/)
