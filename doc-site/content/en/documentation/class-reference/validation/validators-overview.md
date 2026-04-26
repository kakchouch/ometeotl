---
title: "Validators Overview"
---

Sources:
- [src/ometeotl_core/validation/syntactic.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/syntactic.py)
- [src/ometeotl_core/validation/structural.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/structural.py)
- [src/ometeotl_core/validation/temporal.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/temporal.py)
- [src/ometeotl_core/validation/spatial.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/spatial.py)
- [src/ometeotl_core/validation/admissibility.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/admissibility.py)
- [src/ometeotl_core/validation/epistemic.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/epistemic.py)
- [src/ometeotl_core/validation/completeness.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/validation/completeness.py)

Implemented validator families:
- `SyntacticValidator`: JSON/YAML payload parse validity.
- `StructuralValidator`: object shape, fields, relations, and hierarchy checks.
- `TemporalValidator`: time-window coexistence checks.
- `SpatialValidator`: relevant-space presence checks.
- `AdmissibilityValidator`: goal admissibility under actor-perception constraints.
- `EpistemicValidator`: epistemic status coherence checks.
- `CompletenessValidator`: minimum/recommended/full completeness thresholds.
