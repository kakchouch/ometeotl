---
title: "BestResponseCalculator"
---

Source:
- [src/ometeotl_core/game/best_response.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/game/best_response.py)

Local role:
Finds the best-response strategy for a focal actor against a fixed set of opponent strategies, using a prebuilt `NormalFormGame`.

Big-picture role:
An actor can only reason about their best move relative to their beliefs about what others will do. BestResponseCalculator instantiates that conditional rationality: given fixed beliefs about opponents, it identifies the choice that maximises an actor's own outcomes. It is the minimal expression of strategic reasoning in a world where actors are finite, self-interested, and uncertain about each other.

Inheritance:
- standard class (stateless)

Constructor:
- `BestResponseCalculator()` — no arguments

Methods:
- `compute(actor_id, opponent_profile, game) -> BestResponseResult`
  - `actor_id: str` — the focal player whose best response is sought
  - `opponent_profile: StrategyProfile` — fixed strategies for all other players
  - `game: NormalFormGame` — prebuilt payoff matrix
  - returns `BestResponseResult` with the best strategy and all ranked options

Important behavior:
- filters `game.payoff_vectors` to rows where opponent strategy ids match `opponent_profile`
- ranks remaining options descending by `comparison_values` from the utility frame metadata, falling back to the raw utility value; ties broken ascending by strategy id — consistent with the `rank_key` convention in `RankedStrategy`
- raises `ValueError` if `actor_id` is not a player in the game
- raises `ValueError` if any key in `opponent_profile` equals `actor_id`
- raises `ValueError` if any opponent in the profile is not a player in the game
- raises `ValueError` if no matching payoff vectors are found

See also:
- [BestResponseResult](/ometeotl/documentation/class-reference/game/best-response/best-response-result/)
- [NormalFormGame](/ometeotl/documentation/class-reference/game/normal-form/normal-form-game/)
- [RankedStrategy](/ometeotl/documentation/class-reference/game/utility/ranked-strategy/)
