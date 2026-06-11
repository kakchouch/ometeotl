---
title: "reconstruct_model_object"
---

Source:
- [src/ometeotl_core/model/registry.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/model/registry.py)

Local role:
Module-level factory function that reconstructs any [ModelObject](/ometeotl/documentation/class-reference/model/base/model-object/) subclass from its canonical serialized dict.

Big-picture role:
Single deserialization entry point used by [WorldModelRegistry.from_dict](/ometeotl/documentation/class-reference/model/registry/world-model-registry/) and by [AuthorityCommandHandler](/ometeotl/documentation/class-reference/core/authority-command-handler/) when replaying serialized state.

Signature:
```python
def reconstruct_model_object(
    raw_object: Mapping[str, Any],
    object_factories: Optional[Mapping[str, ObjectFactory]] = None,
) -> ModelObject
```

Parameters:
- `raw_object` — canonical serialized dict; must contain an `"object_type"` key matching one of the registered factory keys (case-insensitive)
- `object_factories` — optional caller-supplied overrides; merged on top of the default factory table so custom types extend rather than replace the defaults

Default factory table (`object_type` → class):
| `object_type` | Class |
|---|---|
| `"action"` | [Action](/ometeotl/documentation/class-reference/model/actions/action/) |
| `"actor"` | [Actor](/ometeotl/documentation/class-reference/model/actors/actor/) |
| `"goal"` | [Goal](/ometeotl/documentation/class-reference/model/goals/goal/) |
| `"generic"` | [GenericObject](/ometeotl/documentation/class-reference/model/objects/generic-object/) |
| `"resource"` | [Resource](/ometeotl/documentation/class-reference/model/resources/resource/) |
| `"space"` | [Space](/ometeotl/documentation/class-reference/model/spaces/space/) |
| `"strategy"` | [Strategy](/ometeotl/documentation/class-reference/model/strategies/strategy/) |
| `"world"` | [World](/ometeotl/documentation/class-reference/model/world/world/) |

Notes:
- Default factories are built once and cached at module level (`_DEFAULT_FACTORIES`); the cache is initialized lazily to avoid circular import issues.
- Unknown `object_type` values fall back to `ModelObject.from_dict`.
- When `object_factories` is provided a shallow copy of the default table is taken so the cache is never mutated.

Example:

```python
from ometeotl_core.model.registry import reconstruct_model_object

# Round-trip: serialize then reconstruct any model object by type
raw = actor.to_dict()          # {"object_type": "actor", "id": "actor-1", ...}
obj = reconstruct_model_object(raw)
assert obj.id == "actor-1"

# Extend with a custom domain type
class Vehicle(Actor):
    pass

raw_v = {"object_type": "vehicle", "id": "v-1", ...}
obj2 = reconstruct_model_object(
    raw_v,
    object_factories={"vehicle": Vehicle.from_dict},
)
```

See also:
- [WorldModelRegistry](/ometeotl/documentation/class-reference/model/registry/world-model-registry/)
- [MinimalModelRegistry](/ometeotl/documentation/class-reference/model/registry/minimal-model-registry/)
