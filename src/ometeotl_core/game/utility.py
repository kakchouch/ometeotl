"""Concrete game-layer utility combinators and strategy ranking.

This module keeps domain-neutral model primitives in ``ometeotl_core.model`` while
providing minimal, concrete game-layer utilities for V1 (F-32, G-6, G-11).
The combinators operate on actor perceptions and projected successor
perceptions already produced by the model/projection layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from ometeotl_core.model.actors import Actor
from ometeotl_core.model.base import (
    JsonMap,
    ObjectId,
    _canonical_json_map,
)
from ometeotl_core.model.perception import Perception
from ometeotl_core.model.strategies import Strategy, StrategyNode, StrategyOutcomeBranch
from ometeotl_core.model.utility import UtilityFrame, UtilityFunction


def _as_float_dict(
    values: Mapping[str, float],
) -> dict[str, float]:
    return {str(key): float(value) for key, value in values.items()}


def _normalize_metric_directions(
    metric_order: Sequence[str],
    metric_directions: Optional[Mapping[str, str]],
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for metric_name in metric_order:
        direction = str((metric_directions or {}).get(metric_name) or "maximize")
        if direction not in {"maximize", "minimize"}:
            raise ValueError("Metric direction must be either 'maximize' or 'minimize'")
        normalized[metric_name] = direction
    return normalized


def _extract_comparison_vector(
    frame: UtilityFrame,
) -> list[float]:
    raw_values = frame.metadata.get("comparison_values")
    if isinstance(raw_values, list):
        return [float(value) for value in raw_values]
    if raw_values is not None:
        return [float(raw_values)]
    if frame.is_multi_criteria:
        return [float(value) for value in frame.value]
    return [float(frame.scalar_value)]


def _normalize_weights(weights: Sequence[float]) -> list[float]:
    if not weights:
        raise ValueError("At least one weight is required")
    total = sum(float(weight) for weight in weights)
    if total <= 0.0:
        equal_weight = 1.0 / float(len(weights))
        return [equal_weight for _ in weights]
    return [float(weight) / total for weight in weights]


def _aggregate_comparison_vectors(
    frames: Sequence[UtilityFrame],
    normalized_weights: Sequence[float],
) -> list[float]:
    first_vector = _extract_comparison_vector(frames[0])
    aggregated = [0.0 for _ in first_vector]

    for frame, weight in zip(frames, normalized_weights, strict=False):
        vector = _extract_comparison_vector(frame)
        if len(vector) != len(first_vector):
            raise ValueError(
                "All compared utility frames must expose comparison vectors of the same length"
            )
        for index, value in enumerate(vector):
            aggregated[index] += float(weight) * float(value)

    return aggregated


def _all_branch_weight_map(node: StrategyNode) -> dict[str, float]:
    """Return normalized probability weights for all branches, keyed by branch_id."""
    branches = node.outcome_branches
    if not branches:
        return {}

    if all(b.probability is not None for b in branches):
        raw: dict[str, float] = {b.branch_id: float(b.probability or 0.0) for b in branches}
    else:
        raw = {b.branch_id: 1.0 for b in branches}

    total = sum(raw.values())
    if total <= 0.0:
        equal = 1.0 / float(len(raw))
        return {bid: equal for bid in raw}

    return {bid: w / total for bid, w in raw.items()}


@dataclass
class RankedStrategy:
    """One evaluated strategy together with its aggregate utility."""

    strategy: Strategy
    utility_frame: UtilityFrame
    rank_key: tuple[float, ...]
    terminal_branch_ids: list[ObjectId] = field(default_factory=list)
    terminal_probabilities: JsonMap = field(default_factory=dict)


class WeightedSumUtility(UtilityFunction):
    """Scalar utility built from a weighted sum of named metrics."""

    def __init__(
        self,
        framework_id: str,
        metric_weights: Mapping[str, float],
    ) -> None:
        if not framework_id:
            raise ValueError("WeightedSumUtility framework_id cannot be empty")
        if not metric_weights:
            raise ValueError("WeightedSumUtility metric_weights cannot be empty")

        self._framework_id = framework_id
        self._metric_weights = _as_float_dict(metric_weights)
        self._metric_order = list(self._metric_weights.keys())

    @property
    def framework_id(self) -> str:
        return self._framework_id

    @property
    def is_multi_criteria(self) -> bool:
        return False

    def evaluate(
        self,
        perception: Perception,
        actor: Actor,
        context: JsonMap,
    ) -> UtilityFrame:
        del actor
        metric_values, trace_metadata = self.resolve_numeric_metrics(
            self._metric_order,
            perception=perception,
            context=context,
        )

        weighted_components = {
            metric_name: metric_values[metric_name] * self._metric_weights[metric_name]
            for metric_name in self._metric_order
        }
        total_value = sum(weighted_components.values())

        metadata: JsonMap = {
            **trace_metadata,
            "metric_values": _canonical_json_map(metric_values),
            "metric_weights": _canonical_json_map(self._metric_weights),
            "weighted_components": _canonical_json_map(weighted_components),
            "comparison_values": [float(total_value)],
        }
        return self.build_utility_frame(value=float(total_value), metadata=metadata)


class LexicographicUtility(UtilityFunction):
    """Multi-criteria utility with explicit lexicographic comparison order."""

    def __init__(
        self,
        framework_id: str,
        metric_order: Sequence[str],
        *,
        metric_directions: Optional[Mapping[str, str]] = None,
    ) -> None:
        if not framework_id:
            raise ValueError("LexicographicUtility framework_id cannot be empty")
        if not metric_order:
            raise ValueError("LexicographicUtility metric_order cannot be empty")

        normalized_order = [str(metric_name) for metric_name in metric_order]
        if len(set(normalized_order)) != len(normalized_order):
            raise ValueError(
                "LexicographicUtility metric_order cannot contain duplicates"
            )

        self._framework_id = framework_id
        self._metric_order = normalized_order
        self._metric_directions = _normalize_metric_directions(
            self._metric_order,
            metric_directions,
        )

    @property
    def framework_id(self) -> str:
        return self._framework_id

    @property
    def is_multi_criteria(self) -> bool:
        return True

    def evaluate(
        self,
        perception: Perception,
        actor: Actor,
        context: JsonMap,
    ) -> UtilityFrame:
        del actor
        metric_values, trace_metadata = self.resolve_numeric_metrics(
            self._metric_order,
            perception=perception,
            context=context,
        )
        ordered_values = [
            metric_values[metric_name] for metric_name in self._metric_order
        ]
        comparison_values = [
            (value if self._metric_directions[metric_name] == "maximize" else -value)
            for metric_name, value in zip(
                self._metric_order, ordered_values, strict=False
            )
        ]

        metadata: JsonMap = {
            **trace_metadata,
            "metric_values": _canonical_json_map(metric_values),
            "criteria_directions": _canonical_json_map(self._metric_directions),
            "comparison_values": list(comparison_values),
        }
        return self.build_utility_frame(
            value=list(ordered_values),
            criteria_labels=list(self._metric_order),
            metadata=metadata,
        )


class StrategyRanker:
    """Rank strategies by the utility of their projected terminal perceptions."""

    def __init__(self, utility_function: UtilityFunction) -> None:
        self.utility_function = utility_function

    def evaluate_strategy(
        self,
        strategy: Strategy,
        *,
        actor: Actor,
        context: Optional[JsonMap] = None,
    ) -> RankedStrategy:
        strategy.validate_tree()

        node_index = {node.node_id: node for node in strategy.nodes}
        if strategy.root_node_id not in node_index:
            raise ValueError("Strategy root_node_id must reference an existing node")

        terminal_branch_map: dict[str, StrategyOutcomeBranch] = {}
        terminal_probability_by_branch: dict[str, float] = {}
        stack: list[tuple[StrategyNode, float, tuple[ObjectId, ...]]] = [
            (node_index[strategy.root_node_id], 1.0, tuple())
        ]

        while stack:
            node, path_probability, path = stack.pop()
            if node.node_id in path:
                raise ValueError("StrategyRanker cannot evaluate cyclic strategies")

            branch_weights = _all_branch_weight_map(node)
            if not branch_weights:
                raise ValueError(
                    "StrategyRanker requires all strategy nodes to have at least one outcome branch"
                )

            next_path = (*path, node.node_id)
            for branch in node.outcome_branches:
                weight = branch_weights.get(branch.branch_id, 0.0)
                branch_probability = path_probability * weight
                if branch.child_node_id is not None:
                    child_node = node_index.get(branch.child_node_id)
                    if child_node is None:
                        raise ValueError(
                            "Strategy branch child_node_id must reference an existing node"
                        )
                    stack.append((child_node, branch_probability, next_path))
                elif branch.projected_state is not None:
                    terminal_branch_map[branch.branch_id] = branch
                    terminal_probability_by_branch[branch.branch_id] = (
                        terminal_probability_by_branch.get(branch.branch_id, 0.0)
                        + branch_probability
                    )

        if not terminal_branch_map:
            raise ValueError("StrategyRanker could not resolve any terminal branches")

        terminal_branch_ids = sorted(terminal_branch_map.keys())
        terminal_branches_list: list[StrategyOutcomeBranch] = [
            terminal_branch_map[bid] for bid in terminal_branch_ids
        ]

        normalized_probabilities = _normalize_weights(
            [terminal_probability_by_branch[bid] for bid in terminal_branch_ids]
        )

        frames: list[UtilityFrame] = []
        for branch, probability in zip(
            terminal_branches_list,
            normalized_probabilities,
            strict=False,
        ):
            evaluation_context = dict(context or {})
            evaluation_context.update(
                {
                    "strategy_id": strategy.id,
                    "terminal_branch_id": branch.branch_id,
                    "terminal_probability": probability,
                }
            )
            frames.append(
                self.utility_function.evaluate(
                    branch.projected_state.perception,
                    actor,
                    evaluation_context,
                )
            )

        first_frame = frames[0]
        aggregated_metadata: JsonMap = {
            "strategy_id": strategy.id,
            "aggregation_mode": "probability_weighted_terminal_mean",
            "evaluated_terminal_branch_ids": list(terminal_branch_ids),
            "terminal_probabilities": _canonical_json_map(
                {
                    bid: probability
                    for bid, probability in zip(
                        terminal_branch_ids,
                        normalized_probabilities,
                        strict=False,
                    )
                }
            ),
        }

        comparison_values = _aggregate_comparison_vectors(
            frames, normalized_probabilities
        )
        aggregated_metadata["comparison_values"] = list(comparison_values)

        if first_frame.is_multi_criteria:
            criteria_labels = list(first_frame.criteria_labels)
            aggregated_vector = [0.0 for _ in criteria_labels]
            for frame, probability in zip(
                frames, normalized_probabilities, strict=False
            ):
                if not frame.is_multi_criteria:
                    raise ValueError(
                        "Cannot aggregate mixed scalar and multi-criteria utility frames"
                    )
                if list(frame.criteria_labels) != criteria_labels:
                    raise ValueError(
                        "All aggregated multi-criteria utility frames must use the same criteria_labels"
                    )
                for index, value in enumerate(frame.value):
                    aggregated_vector[index] += float(probability) * float(value)

            aggregated_frame = self.utility_function.build_utility_frame(
                value=list(aggregated_vector),
                criteria_labels=criteria_labels,
                metadata=aggregated_metadata,
            )
        else:
            aggregated_scalar = 0.0
            for frame, probability in zip(
                frames, normalized_probabilities, strict=False
            ):
                if frame.is_multi_criteria:
                    raise ValueError(
                        "Cannot aggregate mixed scalar and multi-criteria utility frames"
                    )
                aggregated_scalar += float(probability) * float(frame.scalar_value)

            aggregated_frame = self.utility_function.build_utility_frame(
                value=float(aggregated_scalar),
                metadata=aggregated_metadata,
            )

        return RankedStrategy(
            strategy=strategy,
            utility_frame=aggregated_frame,
            rank_key=tuple(float(value) for value in comparison_values),
            terminal_branch_ids=list(terminal_branch_ids),
            terminal_probabilities=_canonical_json_map(
                {
                    bid: probability
                    for bid, probability in zip(
                        terminal_branch_ids,
                        normalized_probabilities,
                        strict=False,
                    )
                }
            ),
        )

    def rank_strategies(
        self,
        strategies: Sequence[Strategy],
        *,
        actor: Actor,
        context: Optional[JsonMap] = None,
    ) -> list[RankedStrategy]:
        ranked = [
            self.evaluate_strategy(strategy, actor=actor, context=context)
            for strategy in strategies
        ]
        return sorted(
            ranked,
            key=lambda item: (item.rank_key, item.strategy.id),
            reverse=True,
        )
