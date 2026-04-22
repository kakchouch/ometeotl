---
title: "Validators Overview"
---

Sources:
- [src/masm/validation/syntactic.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/validation/syntactic.py)
- [src/masm/validation/structural.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/validation/structural.py)
- [src/masm/validation/temporal.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/validation/temporal.py)
- [src/masm/validation/spatial.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/validation/spatial.py)
- [src/masm/validation/admissibility.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/validation/admissibility.py)
- [src/masm/validation/epistemic.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/validation/epistemic.py)
- [src/masm/validation/completeness.py](https://github.com/kakchouch/ometeotl/blob/main/src/masm/validation/completeness.py)

Implemented validator families:
- `SyntacticValidator`: JSON/YAML payload parse validity.
- `StructuralValidator`: object shape, fields, relations, and hierarchy checks.
- `TemporalValidator`: time-window coexistence checks.
- `SpatialValidator`: relevant-space presence checks.
- `AdmissibilityValidator`: goal admissibility under actor-perception constraints.
- `EpistemicValidator`: epistemic status coherence checks.
- `CompletenessValidator`: minimum/recommended/full completeness thresholds.
