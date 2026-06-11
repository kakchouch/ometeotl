---
title: "PayoffVector"
---

Source:
- [src/ometeotl_core/game/normal_form.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/normal_form.py)

Local role:
One row of the payoff matrix: a joint strategy profile together with the utility frame each player receives under that profile.

Big-picture role:
Every joint decision produces distinct consequences for each player. A PayoffVector makes those consequences explicit for one particular combination of choices — it is the answer to the hypothetical "what does each player get if everyone plays exactly this way?"

Inheritance:
- standard dataclass

Fields:
- `profile: StrategyProfile` — `dict[str, Strategy]` mapping actor_id → chosen Strategy
- `payoffs: dict[str, UtilityFrame]` — per-actor utility outcomes for this profile

Methods:
- `to_dict() -> JsonMap`

See also:
- [NormalFormGame](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/)
- [PayoffFunction](/ometeotl/documentation/class-reference/game/normal-form/payoff-function/)
