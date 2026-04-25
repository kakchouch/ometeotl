"""Concrete game-layer utility combinators and strategy ranking.

This module keeps domain-neutral model primitives in ``masm.model`` while
providing minimal, concrete game-layer utilities for V1 (F-32, G-6, G-11).
The combinators operate on actor perceptions and projected successor
perceptions already produced by the model/projection layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from masm.model.actors import Actor
from masm.model.base import (
    JsonMap,
    ObjectId,
    _canonical_json_map,
)
from masm.model.perception import Perception
from masm.model.strategies import Strategy, StrategyNode
from masm.model.utility import UtilityFrame, UtilityFunction


def _as_float_dict(
    values: Mapping[str, float],
) -> dict[str, float]:
    return {
        str(key): float(value) for key, value in values.items()
    }


def _normalize_metric_directions(
    metric_order: Sequence[str],
    metric_directions: Optional[Mapping[str, str]],
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for metric_name in metric_order:
        direction = str(
            (metric_directions or {}).get(metric_name)
            or "maximize"
        )
        if direction not in {"maximize", "minimize"}:
            raise ValueError(
                "Metric direction must be either 'maximize' or 'minimize'"
            )
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

    for frame, weight in zip(
        frames, normalized_weights, strict=False
    ):
        vector = _extract_comparison_vector(frame)
        if len(vector) != len(first_vector):
            raise ValueError(
                "All compared utility frames must expose comparison vectors of the same length"
            )
        for index, value in enumerate(vector):
            aggregated[index] += float(weight) * float(value)

    return aggregated


def _branch_weight_map(
    node: StrategyNode,
) -> dict[ObjectId, float]:
    child_branches = [
        branch
        for branch in node.outcome_branches
        if branch.child_node_id is not None
    ]
    if not child_branches:
        return {}

    raw_weight_by_child: dict[str, float] = {}

    if all(
        branch.probability is not None
        for branch in child_branches
    ):
        for branch in child_branches:
            child_id = str(branch.child_node_id)
            raw_weight_by_child[child_id] = (
                raw_weight_by_child.get(child_id, 0.0)
                + float(branch.probability or 0.0)
            )
    else:
        # When probabilities are absent, each branch contributes one unit.
        for branch in child_branches:
            child_id = str(branch.child_node_id)
            raw_weight_by_child[child_id] = (
                raw_weight_by_child.get(child_id, 0.0) + 1.0
            )

    total_raw = sum(raw_weight_by_child.values())
    if total_raw <= 0.0:
        equal_weight = 1.0 / float(len(raw_weight_by_child))
        return {
            child_id: equal_weight
            for child_id in sorted(raw_weight_by_child.keys())
        }

    return {
        child_id: raw_weight / total_raw
        for child_id, raw_weight in sorted(
            raw_weight_by_child.items()
        )
    }


@dataclass
class RankedStrategy:
    """One evaluated strategy together with its aggregate utility."""

    strategy: Strategy
    utility_frame: UtilityFrame
    rank_key: tuple[float, ...]
    terminal_node_ids: list[ObjectId] = field(
        default_factory=list
    )
    terminal_probabilities: JsonMap = field(default_factory=dict)


class WeightedSumUtility(UtilityFunction):
    """Scalar utility built from a weighted sum of named metrics."""

    def __init__(
        self,
        framework_id: str,
        metric_weights: Mapping[str, float],
    ) -> None:
        if not framework_id:
            raise ValueError(
                "WeightedSumUtility framework_id cannot be empty"
            )
        if not metric_weights:
            raise ValueError(
                "WeightedSumUtility metric_weights cannot be empty"
            )

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
        metric_values, trace_metadata = (
            self.resolve_numeric_metrics(
                self._metric_order,
                perception=perception,
                context=context,
            )
        )

        weighted_components = {
            metric_name: metric_values[metric_name]
            * self._metric_weights[metric_name]
            for metric_name in self._metric_order
        }
        total_value = sum(weighted_components.values())

        metadata: JsonMap = {
            **trace_metadata,
            "metric_values": _canonical_json_map(metric_values),
            "metric_weights": _canonical_json_map(
                self._metric_weights
            ),
            "weighted_components": _canonical_json_map(
                weighted_components
            ),
            "comparison_values": [float(total_value)],
        }
        return self.build_utility_frame(
            value=float(total_value), metadata=metadata
        )


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
            raise ValueError(
                "LexicographicUtility framework_id cannot be empty"
            )
        if not metric_order:
            raise ValueError(
                "LexicographicUtility metric_order cannot be empty"
            )

        normalized_order = [
            str(metric_name) for metric_name in metric_order
        ]
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
        metric_values, trace_metadata = (
            self.resolve_numeric_metrics(
                self._metric_order,
                perception=perception,
                context=context,
            )
        )
        ordered_values = [
            metric_values[metric_name]
            for metric_name in self._metric_order
        ]
        comparison_values = [
            (
                value
                if self._metric_directions[metric_name]
                == "maximize"
                else -value
            )
            for metric_name, value in zip(
                self._metric_order, ordered_values, strict=False
            )
        ]

        metadata: JsonMap = {
            **trace_metadata,
            "metric_values": _canonical_json_map(metric_values),
            "criteria_directions": _canonical_json_map(
                self._metric_directions
            ),
            "comparison_values": list(comparison_values),
        }
        return self.build_utility_frame(
            value=list(ordered_values),
            criteria_labels=list(self._metric_order),
            metadata=metadata,
        )


class StrategyRanker:
    """Rank strategies by the utility of their projected terminal perceptions."""

    def __init__(
        self, utility_function: UtilityFunction
    ) -> None:
        self.utility_function = utility_function

    def evaluate_strategy(
        self,
        strategy: Strategy,
        *,
        actor: Actor,
        context: Optional[JsonMap] = None,
    ) -> RankedStrategy:
        strategy.validate_tree()

        node_index = {
            node.node_id: node for node in strategy.nodes
        }
        if strategy.root_node_id not in node_index:
            raise ValueError(
                "Strategy root_node_id must reference an existing node"
            )

        terminal_node_index: dict[str, StrategyNode] = {}
        terminal_probability_by_node: dict[str, float] = {}
        stack: list[
            tuple[StrategyNode, float, tuple[ObjectId, ...]]
        ] = [(node_index[strategy.root_node_id], 1.0, tuple())]

        while stack:
            node, path_probability, path = stack.pop()
            if node.node_id in path:
                raise ValueError(
                    "StrategyRanker cannot evaluate cyclic strategies"
                )

            child_weights = _branch_weight_map(node)
            if not child_weights:
                if node.projected_state is None:
                    raise ValueError(
                        "StrategyRanker requires terminal strategy nodes to carry a projected_state"
                    )
                terminal_node_index[node.node_id] = node
                terminal_probability_by_node[node.node_id] = (
                    terminal_probability_by_node.get(
                        node.node_id, 0.0
                    )
                    + path_probability
                )
                continue

            next_path = (*path, node.node_id)
            for (
                child_node_id,
                branch_weight,
            ) in child_weights.items():
                child_node = node_index.get(child_node_id)
                if child_node is None:
                    raise ValueError(
                        "Strategy branch child_node_id must reference an existing node"
                    )
                stack.append(
                    (
                        child_node,
                        path_probability * branch_weight,
                        next_path,
                    )
                )

        if not terminal_node_index:
            raise ValueError(
                "StrategyRanker could not resolve any terminal nodes"
            )

        terminal_node_ids = sorted(terminal_node_index.keys())
        terminal_nodes = [
            terminal_node_index[node_id]
            for node_id in terminal_node_ids
        ]

        normalized_probabilities = _normalize_weights(
            [
                terminal_probability_by_node[node_id]
                for node_id in terminal_node_ids
            ]
        )

        frames: list[UtilityFrame] = []
        for node, probability in zip(
            terminal_nodes,
            normalized_probabilities,
            strict=False,
        ):
            evaluation_context = dict(context or {})
            evaluation_context.update(
                {
                    "strategy_id": strategy.id,
                    "terminal_node_id": node.node_id,
                    "terminal_probability": probability,
                }
            )
            frames.append(
                self.utility_function.evaluate(
                    node.projected_state.perception,
                    actor,
                    evaluation_context,
                )
            )

        first_frame = frames[0]
        aggregated_metadata: JsonMap = {
            "strategy_id": strategy.id,
            "aggregation_mode": "probability_weighted_terminal_mean",
            "evaluated_terminal_node_ids": list(
                terminal_node_ids
            ),
            "terminal_probabilities": _canonical_json_map(
                {
                    node_id: probability
                    for node_id, probability in zip(
                        terminal_node_ids,
                        normalized_probabilities,
                        strict=False,
                    )
                }
            ),
        }

        comparison_values = _aggregate_comparison_vectors(
            frames, normalized_probabilities
        )
        aggregated_metadata["comparison_values"] = list(
            comparison_values
        )

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
                if (
                    list(frame.criteria_labels)
                    != criteria_labels
                ):
                    raise ValueError(
                        "All aggregated multi-criteria utility frames must use the same criteria_labels"
                    )
                for index, value in enumerate(frame.value):
                    aggregated_vector[index] += float(
                        probability
                    ) * float(value)

            aggregated_frame = (
                self.utility_function.build_utility_frame(
                    value=list(aggregated_vector),
                    criteria_labels=criteria_labels,
                    metadata=aggregated_metadata,
                )
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
                aggregated_scalar += float(probability) * float(
                    frame.scalar_value
                )

            aggregated_frame = (
                self.utility_function.build_utility_frame(
                    value=float(aggregated_scalar),
                    metadata=aggregated_metadata,
                )
            )

        return RankedStrategy(
            strategy=strategy,
            utility_frame=aggregated_frame,
            rank_key=tuple(
                float(value) for value in comparison_values
            ),
            terminal_node_ids=list(terminal_node_ids),
            terminal_probabilities=_canonical_json_map(
                {
                    node_id: probability
                    for node_id, probability in zip(
                        terminal_node_ids,
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
            self.evaluate_strategy(
                strategy, actor=actor, context=context
            )
            for strategy in strategies
        ]
        return sorted(
            ranked,
            key=lambda item: (item.rank_key, item.strategy.id),
            reverse=True,
        )
