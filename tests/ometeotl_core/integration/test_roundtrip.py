"""Integration tests: full generation roundtrip and 2-actor game scenario.

Test 1 covers the complete chain:
  context → pipeline → generated objects → IO export → to_llm_view() → parse → validate

Test 2 covers a concrete 2-actor game world:
  goals, strategies, projected perception states, and utility ranking end to end.
"""

import json

from tests.ometeotl_core._artifact_utils import write_json_artifact, write_text_artifact

from ometeotl_core.game.utility import StrategyRanker, WeightedSumUtility
from ometeotl_core.generation import (
    ContextualGenerationPipeline,
    GenerationContext,
    GenerationPlacement,
)
from ometeotl_core.io import (
    world_from_json,
    world_to_json,
    world_to_llm_view,
    world_to_yaml,
)
from ometeotl_core.model.actors import Actor
from ometeotl_core.model.goals import Goal
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.projection import ProjectedPerceptionState
from ometeotl_core.model.resources import Resource
from ometeotl_core.model.strategies import Strategy, StrategyNode, StrategyOutcomeBranch
from ometeotl_core.model.world import World


def test_generation_roundtrip_full_chain():
    """Full chain: context → pipeline → generated objects → IO export → to_llm_view() → parse → validate."""
    pipeline = ContextualGenerationPipeline()

    # 1. Context → pipeline → World
    result = pipeline.generate(
        GenerationContext(
            kind="world",
            id="world-roundtrip-1",
            label="Roundtrip Test World",
            spaces=[
                GenerationContext(kind="space", id="zone-north", label="Northern Zone"),
                GenerationContext(kind="space", id="zone-south", label="Southern Zone"),
            ],
            actors=[
                GenerationContext(kind="actor", id="player-red", label="Player Red"),
                GenerationContext(kind="actor", id="player-blue", label="Player Blue"),
            ],
            resources=[
                GenerationContext(kind="resource", id="supply-depot"),
            ],
            placements=[
                GenerationPlacement(object_id="player-red", space_id="zone-north"),
                GenerationPlacement(object_id="player-blue", space_id="zone-south"),
            ],
        )
    )
    world = result.generated
    assert isinstance(world, World)
    assert world.get_space("zone-north") is not None
    assert world.get_space("zone-south") is not None
    assert isinstance(world.model_registry.get("player-red"), Actor)
    assert isinstance(world.model_registry.get("player-blue"), Actor)
    assert isinstance(world.model_registry.get("supply-depot"), Resource)
    assert "player-red" in world.space_object_graph.list_objects_in_space("zone-north")
    assert "player-blue" in world.space_object_graph.list_objects_in_space("zone-south")

    # 2. Generated objects: goal, strategy, perception via pipeline
    red_goal = pipeline.generate(
        GenerationContext(
            kind="goal",
            id="goal-red-control",
            metadata={
                "actor_id": "player-red",
                "kind": "final",
                "priority": 1.0,
                "target_condition": {"control": "zone-north"},
            },
        )
    ).generated
    assert isinstance(red_goal, Goal)
    assert red_goal.actor_id == "player-red"

    red_strategy = pipeline.generate(
        GenerationContext(
            kind="strategy",
            id="strategy-red-advance",
            metadata={
                "actor_id": "player-red",
                "goal_id": "goal-red-control",
                "root_node_id": "node-red-advance",
                "action_id": "action-red-advance",
            },
        )
    ).generated

    red_perception = pipeline.generate(
        GenerationContext(
            kind="perception",
            id="perception-red-1",
            metadata={
                "actor_id": "player-red",
                "source_id": "world-roundtrip-1",
                "perceived_spaces": {
                    "zone-north": {
                        "space": {"id": "zone-north", "object_type": "space"},
                        "epistemic_status": "certain",
                    },
                    "zone-south": {
                        "space": {"id": "zone-south", "object_type": "space"},
                        "epistemic_status": "believed",
                    },
                },
                "perceived_memberships": [
                    {
                        "membership": {
                            "object_id": "player-red",
                            "space_id": "zone-north",
                            "role": "occupies",
                        },
                        "epistemic_status": "certain",
                    }
                ],
            },
        )
    ).generated

    # 3. IO export: JSON, YAML, world LLM view
    json_text = world_to_json(world)
    yaml_text = world_to_yaml(world)
    llm_view = world_to_llm_view(world)

    assert json.loads(json_text)["id"] == "world-roundtrip-1"
    assert llm_view["type"] == "world"
    assert llm_view["members_summary"]["total_actors"] == 2
    assert llm_view["members_summary"]["total_resources"] == 1
    assert "player-red" in llm_view["members"]["actors"]
    assert "player-blue" in llm_view["members"]["actors"]
    assert "supply-depot" in llm_view["members"]["resources"]

    # 4. to_llm_view() on each generated object type
    actor_view = world.model_registry.get("player-red").to_llm_view()
    assert actor_view["type"] == "actor"
    assert actor_view["kind"] == "generic"

    goal_view = red_goal.to_llm_view()
    assert goal_view["type"] == "goal"
    assert goal_view["epistemic"]["status"] == "certain"

    strategy_view = red_strategy.to_llm_view()
    assert strategy_view["type"] == "strategy"

    perception_view = red_perception.to_llm_view()
    assert perception_view["type"] == "perception"
    assert perception_view["epistemic"]["has_perception"] is True
    assert "zone-north" in perception_view["perception"]["perceived_spaces"]

    # 5. Parse → validate
    import_result = world_from_json(json_text)
    assert import_result.parsed_format == "json"
    assert import_result.validation.valid is True
    restored = import_result.world
    assert restored.id == "world-roundtrip-1"
    assert restored.get_space("zone-north") is not None
    assert restored.get_space("zone-south") is not None
    assert "player-red" in restored.space_object_graph.list_objects_in_space("zone-north")
    assert "player-blue" in restored.space_object_graph.list_objects_in_space("zone-south")
    assert isinstance(restored.model_registry.get("player-red"), Actor)
    assert isinstance(restored.model_registry.get("supply-depot"), Resource)

    # Artifacts
    artifact_path = write_json_artifact(
        layer="integration",
        name="roundtrip_full_chain",
        payload={
            "world": world.to_dict(),
            "world_llm_view": llm_view,
            "goal_llm_view": goal_view,
            "strategy_llm_view": strategy_view,
            "perception_llm_view": perception_view,
            "roundtrip_validation": import_result.validation.summary,
        },
    )
    assert artifact_path.name == "roundtrip_full_chain.json"
    write_text_artifact(
        layer="integration",
        name="roundtrip_world_export",
        content=yaml_text,
        extension="yaml",
    )


def _make_terminal_strategy(
    *,
    strategy_id: str,
    actor_id: str,
    goal_id: str,
    root_node_id: str,
    action_id: str,
    perception_id: str,
    world_id: str,
    **ctx_values: float,
) -> Strategy:
    """Build a single-node strategy with one terminal branch carrying a projected state."""
    return Strategy(
        id=strategy_id,
        actor_id=actor_id,
        goal_id=goal_id,
        root_node_id=root_node_id,
        nodes=[
            StrategyNode(
                node_id=root_node_id,
                action_id=action_id,
                outcome_branches=[
                    StrategyOutcomeBranch(
                        branch_id=f"{root_node_id}:terminal",
                        label="outcome",
                        child_node_id=None,
                        projected_state=ProjectedPerceptionState(
                            source_perception_id=f"p-source-{actor_id}",
                            generating_action_id=action_id,
                            perception=Perception(
                                id=perception_id,
                                actor_id=actor_id,
                                source_id=world_id,
                                context=dict(ctx_values),
                            ),
                        ),
                    )
                ],
            )
        ],
    )


def test_two_actor_game_world_goals_strategies_and_utility_ranking():
    """2-actor game: wires goals, strategies, and utility ranking end to end.

    Scenario:
      - Arena world: zone-north and zone-south
      - Player Red occupies zone-north, Player Blue occupies zone-south
      - Each actor has a final goal and two competing strategies
      - Utility = gain * 1.0 + risk * (-0.5)
        - Red aggressive  (gain=8, risk=6): score 5.0
        - Red defensive   (gain=4, risk=2): score 3.0  → Red prefers aggressive
        - Blue aggressive (gain=7, risk=6): score 4.0
        - Blue defensive  (gain=5, risk=1): score 4.5  → Blue prefers defensive
    """
    pipeline = ContextualGenerationPipeline()

    # World with 2 actors and 2 zones
    world = pipeline.generate(
        GenerationContext(
            kind="world",
            id="world-arena-1",
            label="Arena",
            spaces=[
                GenerationContext(kind="space", id="zone-north"),
                GenerationContext(kind="space", id="zone-south"),
            ],
            actors=[
                GenerationContext(kind="actor", id="player-red", label="Player Red"),
                GenerationContext(kind="actor", id="player-blue", label="Player Blue"),
            ],
            placements=[
                GenerationPlacement(object_id="player-red", space_id="zone-north"),
                GenerationPlacement(object_id="player-blue", space_id="zone-south"),
            ],
        )
    ).generated
    assert isinstance(world, World)

    # Goals via pipeline, registered in world registry
    red_goal = pipeline.generate(
        GenerationContext(
            kind="goal",
            id="goal-red-control",
            registration_policy="require",
            metadata={
                "actor_id": "player-red",
                "kind": "final",
                "priority": 1.0,
                "target_condition": {"control": "zone-north"},
            },
        ),
        world=world,
    ).generated
    blue_goal = pipeline.generate(
        GenerationContext(
            kind="goal",
            id="goal-blue-control",
            registration_policy="require",
            metadata={
                "actor_id": "player-blue",
                "kind": "final",
                "priority": 1.0,
                "target_condition": {"control": "zone-south"},
            },
        ),
        world=world,
    ).generated
    assert isinstance(red_goal, Goal)
    assert isinstance(blue_goal, Goal)
    assert world.model_registry.get("goal-red-control") is red_goal
    assert world.model_registry.get("goal-blue-control") is blue_goal

    red_actor = world.model_registry.get("player-red")
    blue_actor = world.model_registry.get("player-blue")
    assert isinstance(red_actor, Actor)
    assert isinstance(blue_actor, Actor)

    # Strategies with projected perception states for utility evaluation
    red_aggressive = _make_terminal_strategy(
        strategy_id="strategy-red-aggressive",
        actor_id="player-red",
        goal_id="goal-red-control",
        root_node_id="node-red-agg",
        action_id="action-red-agg",
        perception_id="p-red-agg",
        world_id="world-arena-1",
        gain=8.0,
        risk=6.0,
    )
    red_defensive = _make_terminal_strategy(
        strategy_id="strategy-red-defensive",
        actor_id="player-red",
        goal_id="goal-red-control",
        root_node_id="node-red-def",
        action_id="action-red-def",
        perception_id="p-red-def",
        world_id="world-arena-1",
        gain=4.0,
        risk=2.0,
    )
    blue_aggressive = _make_terminal_strategy(
        strategy_id="strategy-blue-aggressive",
        actor_id="player-blue",
        goal_id="goal-blue-control",
        root_node_id="node-blue-agg",
        action_id="action-blue-agg",
        perception_id="p-blue-agg",
        world_id="world-arena-1",
        gain=7.0,
        risk=6.0,
    )
    blue_defensive = _make_terminal_strategy(
        strategy_id="strategy-blue-defensive",
        actor_id="player-blue",
        goal_id="goal-blue-control",
        root_node_id="node-blue-def",
        action_id="action-blue-def",
        perception_id="p-blue-def",
        world_id="world-arena-1",
        gain=5.0,
        risk=1.0,
    )

    # Utility ranking: gain * 1.0 + risk * (-0.5)
    utility = WeightedSumUtility("arena-strategy", {"gain": 1.0, "risk": -0.5})
    ranker = StrategyRanker(utility)

    red_ranked = ranker.rank_strategies(
        [red_aggressive, red_defensive], actor=red_actor
    )
    blue_ranked = ranker.rank_strategies(
        [blue_aggressive, blue_defensive], actor=blue_actor
    )

    # Red: aggressive (8 - 3 = 5.0) beats defensive (4 - 1 = 3.0)
    assert [r.strategy.id for r in red_ranked] == [
        "strategy-red-aggressive",
        "strategy-red-defensive",
    ]
    assert red_ranked[0].utility_frame.value == 5.0
    assert red_ranked[1].utility_frame.value == 3.0

    # Blue: defensive (5 - 0.5 = 4.5) beats aggressive (7 - 3 = 4.0)
    assert [r.strategy.id for r in blue_ranked] == [
        "strategy-blue-defensive",
        "strategy-blue-aggressive",
    ]
    assert blue_ranked[0].utility_frame.value == 4.5
    assert blue_ranked[1].utility_frame.value == 4.0

    # to_llm_view() on top-ranked strategies for each actor
    red_top_view = red_ranked[0].strategy.to_llm_view()
    blue_top_view = blue_ranked[0].strategy.to_llm_view()
    assert red_top_view["type"] == "strategy"
    assert blue_top_view["type"] == "strategy"

    # Artifact
    artifact_path = write_json_artifact(
        layer="integration",
        name="two_actor_game_scenario",
        payload={
            "world": world.to_dict(),
            "goals": {
                "player-red": red_goal.to_dict(),
                "player-blue": blue_goal.to_dict(),
            },
            "strategy_llm_views": {
                "red_top": red_top_view,
                "blue_top": blue_top_view,
            },
            "utility_ranking": {
                "player-red": [
                    {"strategy": r.strategy.id, "utility": r.utility_frame.value}
                    for r in red_ranked
                ],
                "player-blue": [
                    {"strategy": r.strategy.id, "utility": r.utility_frame.value}
                    for r in blue_ranked
                ],
            },
        },
    )
    assert artifact_path.name == "two_actor_game_scenario.json"
