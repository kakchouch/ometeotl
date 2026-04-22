"""Tests for masm.model.utility."""

import pytest

from masm.model.utility import UtilityFunction, UtilityFrame
from masm.model.perception import Perception
from masm.model.actors import Actor


def test_utility_frame_scalar_instantiation():
    """UtilityFrame instantiates with a scalar value."""
    frame = UtilityFrame(
        value=0.75,
        framework_id="wealth-maximization",
    )

    assert frame.value == 0.75
    assert frame.framework_id == "wealth-maximization"
    assert frame.is_multi_criteria is False
    assert frame.criteria_labels == []
    assert frame.metadata == {}


def test_utility_frame_vector_instantiation():
    """UtilityFrame instantiates with a vector value."""
    frame = UtilityFrame(
        value=[0.8, 0.6, 0.5],
        framework_id="multi-objective",
        criteria_labels=["wealth", "health", "happiness"],
    )

    assert frame.value == [0.8, 0.6, 0.5]
    assert frame.framework_id == "multi-objective"
    assert frame.is_multi_criteria is True
    assert frame.criteria_labels == ["wealth", "health", "happiness"]


def test_utility_frame_empty_framework_id_rejected():
    """UtilityFrame rejects empty framework_id."""
    with pytest.raises(ValueError, match="framework_id cannot be empty"):
        UtilityFrame(
            value=0.5,
            framework_id="",
        )


def test_utility_frame_vector_criteria_labels_length_mismatch():
    """UtilityFrame rejects mismatched criteria_labels and vector length."""
    with pytest.raises(ValueError, match="criteria_labels length must match"):
        UtilityFrame(
            value=[0.8, 0.6],
            framework_id="test",
            criteria_labels=["a", "b", "c"],  # 3 labels but 2 values
        )


def test_utility_frame_scalar_value_property():
    """scalar_value property returns scalar value."""
    frame = UtilityFrame(
        value=0.85,
        framework_id="test",
    )
    assert frame.scalar_value == 0.85


def test_utility_frame_scalar_value_property_on_vector_raises():
    """scalar_value property raises on vector value."""
    frame = UtilityFrame(
        value=[0.8, 0.6],
        framework_id="test",
    )
    with pytest.raises(ValueError, match="Cannot extract scalar_value"):
        _ = frame.scalar_value


def test_utility_frame_serialization_scalar():
    """UtilityFrame with scalar value serializes and deserializes correctly."""
    frame = UtilityFrame(
        value=0.9,
        framework_id="wealth",
        metadata={"reason": "high_resources"},
    )

    frame_dict = frame.to_dict()
    assert frame_dict["value"] == 0.9
    assert frame_dict["framework_id"] == "wealth"
    assert frame_dict["criteria_labels"] == []
    assert frame_dict["metadata"] == {"reason": "high_resources"}

    recovered_frame = UtilityFrame.from_dict(frame_dict)
    assert recovered_frame.value == frame.value
    assert recovered_frame.framework_id == frame.framework_id
    assert recovered_frame.is_multi_criteria == frame.is_multi_criteria


def test_utility_frame_serialization_vector():
    """UtilityFrame with vector value serializes and deserializes correctly."""
    frame = UtilityFrame(
        value=[0.8, 0.5, 0.3],
        framework_id="multi",
        criteria_labels=["a", "b", "c"],
        metadata={"timestamp": 42},
    )

    frame_dict = frame.to_dict()
    assert frame_dict["value"] == [0.8, 0.5, 0.3]
    assert frame_dict["criteria_labels"] == ["a", "b", "c"]
    assert frame_dict["metadata"] == {"timestamp": 42}

    recovered_frame = UtilityFrame.from_dict(frame_dict)
    assert recovered_frame.value == frame.value
    assert recovered_frame.criteria_labels == frame.criteria_labels
    assert recovered_frame.is_multi_criteria is True


def test_utility_frame_from_dict_scalar_none():
    """UtilityFrame.from_dict handles None scalar value as 0.0."""
    frame = UtilityFrame.from_dict(
        {
            "value": None,
            "framework_id": "test",
        }
    )
    assert frame.value == 0.0


def test_utility_function_cannot_be_instantiated():
    """UtilityFunction is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        UtilityFunction()  # type: ignore


def test_utility_function_incomplete_subclass_is_abstract():
    """UtilityFunction subclass missing required members remains abstract."""

    class IncompleteUtility(UtilityFunction):
        """Missing framework_id, is_multi_criteria, and evaluate implementations."""

        pass

    abstract_methods = IncompleteUtility.__abstractmethods__
    assert abstract_methods
    assert "framework_id" in abstract_methods
    assert "is_multi_criteria" in abstract_methods
    assert "evaluate" in abstract_methods


def test_utility_function_minimal_concrete_subclass():
    """A minimal concrete UtilityFunction subclass works correctly."""

    class SimpleUtility(UtilityFunction):
        def __init__(self, framework_id: str, value: float):
            self._framework_id = framework_id
            self._value = value

        @property
        def framework_id(self) -> str:
            return self._framework_id

        @property
        def is_multi_criteria(self) -> bool:
            return False

        def evaluate(self, perception, actor, context):
            del perception, actor, context
            return UtilityFrame(
                value=self._value,
                framework_id=self._framework_id,
            )

    utility = SimpleUtility("test-framework", 0.75)
    assert utility.framework_id == "test-framework"
    assert utility.is_multi_criteria is False

    frame = utility.evaluate(
        perception=Perception(
            id="test-percep",
            actor_id="actor-1",
            source_id="world-1",
        ),
        actor=Actor(id="actor-1"),
        context={},
    )
    assert isinstance(frame, UtilityFrame)
    assert frame.value == 0.75
    assert frame.framework_id == "test-framework"


def test_utility_function_multi_criteria_subclass():
    """A multi-criteria UtilityFunction subclass works correctly."""

    class MultiCriteriaUtility(UtilityFunction):
        def __init__(self, framework_id: str):
            self._framework_id = framework_id

        @property
        def framework_id(self) -> str:
            return self._framework_id

        @property
        def is_multi_criteria(self) -> bool:
            return True

        def evaluate(self, perception, actor, context):
            del perception, actor, context
            return UtilityFrame(
                value=[0.8, 0.6, 0.4],
                framework_id=self._framework_id,
                criteria_labels=["criterion_a", "criterion_b", "criterion_c"],
            )

    utility = MultiCriteriaUtility("multi-framework")
    assert utility.framework_id == "multi-framework"
    assert utility.is_multi_criteria is True

    frame = utility.evaluate(
        perception=Perception(
            id="test-percep",
            actor_id="actor-1",
            source_id="world-1",
        ),
        actor=Actor(id="actor-1"),
        context={},
    )
    assert frame.is_multi_criteria is True
    assert frame.value == [0.8, 0.6, 0.4]
    assert frame.criteria_labels == ["criterion_a", "criterion_b", "criterion_c"]


def test_utility_function_evaluation_with_context():
    """UtilityFunction.evaluate can use context to compute utility."""

    class ContextAwareUtility(UtilityFunction):
        @property
        def framework_id(self) -> str:
            return "context-framework"

        @property
        def is_multi_criteria(self) -> bool:
            return False

        def evaluate(self, perception, actor, context):
            del perception, actor
            # Use context to scale utility
            scale = float(context.get("scale", 1.0))
            base_value = float(context.get("base_value", 0.5))
            return UtilityFrame(
                value=base_value * scale,
                framework_id=self.framework_id,
            )

    utility = ContextAwareUtility()
    frame = utility.evaluate(
        perception=Perception(
            id="test-percep",
            actor_id="actor-1",
            source_id="world-1",
        ),
        actor=Actor(id="actor-1"),
        context={"scale": 2.0, "base_value": 0.75},
    )
    assert frame.value == 1.5  # 0.75 * 2.0


def test_utility_frame_metadata_preservation():
    """UtilityFrame preserves metadata through serialization."""
    original_metadata = {
        "computation_time_ms": 42,
        "confidence": 0.95,
        "source": "projection",
    }
    frame = UtilityFrame(
        value=0.8,
        framework_id="test",
        metadata=original_metadata,
    )

    frame_dict = frame.to_dict()
    recovered_frame = UtilityFrame.from_dict(frame_dict)
    assert recovered_frame.metadata == original_metadata


def test_utility_function_resolve_numeric_metrics_default_zero_policy():
    """Default-neutral stance uses 0.0 fallback and exposes policy metadata."""

    class MetricResolverUtility(UtilityFunction):
        @property
        def framework_id(self) -> str:
            return "resolver-framework"

        @property
        def is_multi_criteria(self) -> bool:
            return False

        def evaluate(self, perception, actor, context):
            del actor
            values, trace = self.resolve_numeric_metrics(
                ["known", "missing", "override", "bad"],
                perception=perception,
                context=context,
            )
            return self.build_utility_frame(
                value=(
                    values["known"]
                    + values["missing"]
                    + values["override"]
                    + values["bad"]
                ),
                metadata=trace,
            )

    utility = MetricResolverUtility()
    frame = utility.evaluate(
        perception=Perception(
            id="perception-metrics",
            actor_id="actor-1",
            source_id="world-1",
            context={"known": 2.5, "bad": "not-a-number"},
        ),
        actor=Actor(id="actor-1"),
        context={
            "metric_overrides": {"override": 3.0},
        },
    )

    assert frame.value == 5.5
    assert frame.metadata["missing_metric_policy"] == "default_neutral"
    assert frame.metadata["missing_metric_default"] == 0.0
    assert frame.metadata["missing_metric_strict_invalid"] is False
    assert frame.metadata["missing_metrics"] == ["bad", "missing"]
    assert frame.metadata["fallback_applied_count"] == 2
    assert frame.metadata["total_metrics"] == 4
    assert frame.metadata["fallback_ratio"] == 0.5
    assert frame.metadata["fallback_dominance_threshold"] == 0.5
    assert frame.metadata["fallback_dominates"] is False
    assert frame.metadata["metric_sources"]["known"] == "perception.context"
    assert frame.metadata["metric_sources"]["override"] == "context.metric_overrides"
    assert frame.metadata["metric_sources"]["missing"] == "default_missing"
    assert frame.metadata["metric_sources"]["bad"] == "default_invalid"


def test_utility_function_resolve_numeric_metrics_default_pessimistic_policy():
    """Default-pessimistic stance uses a negative fallback by default."""

    class FearPolicyUtility(UtilityFunction):
        @property
        def framework_id(self) -> str:
            return "fear-framework"

        @property
        def is_multi_criteria(self) -> bool:
            return False

        def evaluate(self, perception, actor, context):
            del actor
            values, trace = self.resolve_numeric_metrics(
                ["known", "missing", "invalid"],
                perception=perception,
                context=context,
            )
            return self.build_utility_frame(
                value=values["known"] + values["missing"] + values["invalid"],
                metadata=trace,
            )

    utility = FearPolicyUtility()
    frame = utility.evaluate(
        perception=Perception(
            id="perception-fear",
            actor_id="actor-1",
            source_id="world-1",
            context={"known": 4.0, "invalid": "bad"},
        ),
        actor=Actor(id="actor-1"),
        context={"missing_metric_policy": "default_pessimistic"},
    )

    assert frame.value == 2.0  # 4.0 + (-1.0) + (-1.0)
    assert frame.metadata["missing_metric_policy"] == "default_pessimistic"
    assert frame.metadata["missing_metric_default"] == -1.0
    assert frame.metadata["missing_metrics"] == ["invalid", "missing"]
    assert frame.metadata["metric_sources"]["missing"] == "default_missing"
    assert frame.metadata["metric_sources"]["invalid"] == "default_invalid"


def test_utility_function_resolve_numeric_metrics_policy_is_easily_overridable():
    """Context can override fallback value while keeping default-neutral as preferred stance."""

    class OverridePolicyUtility(UtilityFunction):
        @property
        def framework_id(self) -> str:
            return "override-framework"

        @property
        def is_multi_criteria(self) -> bool:
            return False

        def evaluate(self, perception, actor, context):
            del actor
            values, trace = self.resolve_numeric_metrics(
                ["m1", "m2"],
                perception=perception,
                context=context,
            )
            return self.build_utility_frame(
                value=values["m1"] + values["m2"], metadata=trace
            )

    utility = OverridePolicyUtility()
    frame = utility.evaluate(
        perception=Perception(
            id="perception-override",
            actor_id="actor-1",
            source_id="world-1",
        ),
        actor=Actor(id="actor-1"),
        context={
            "missing_metric_policy": "default_neutral",
            "missing_metric_default": -0.25,
        },
    )

    assert frame.value == -0.5
    assert frame.metadata["missing_metric_policy"] == "default_neutral"
    assert frame.metadata["missing_metric_default"] == -0.25


def test_utility_function_resolve_numeric_metrics_invalid_policy_falls_back_to_default_neutral():
    """Unknown policy names must safely fall back to the default-neutral stance."""

    class InvalidPolicyUtility(UtilityFunction):
        @property
        def framework_id(self) -> str:
            return "invalid-policy-framework"

        @property
        def is_multi_criteria(self) -> bool:
            return False

        def evaluate(self, perception, actor, context):
            del actor
            values, trace = self.resolve_numeric_metrics(
                ["missing_metric"],
                perception=perception,
                context=context,
            )
            return self.build_utility_frame(
                value=values["missing_metric"], metadata=trace
            )

    utility = InvalidPolicyUtility()
    frame = utility.evaluate(
        perception=Perception(
            id="perception-invalid-policy",
            actor_id="actor-1",
            source_id="world-1",
        ),
        actor=Actor(id="actor-1"),
        context={"missing_metric_policy": "aggressive_unknown_mode"},
    )

    assert frame.value == 0.0
    assert frame.metadata["missing_metric_policy"] == "default_neutral"
    assert frame.metadata["missing_metric_default"] == 0.0
    assert frame.metadata["missing_metrics"] == ["missing_metric"]


def test_utility_function_resolve_numeric_metrics_pessimistic_policy_custom_default_override():
    """Default-pessimistic stance supports explicit custom negative fallback."""

    class FearOverrideUtility(UtilityFunction):
        @property
        def framework_id(self) -> str:
            return "fear-override-framework"

        @property
        def is_multi_criteria(self) -> bool:
            return False

        def evaluate(self, perception, actor, context):
            del actor
            values, trace = self.resolve_numeric_metrics(
                ["known", "unknown"],
                perception=perception,
                context=context,
            )
            return self.build_utility_frame(
                value=values["known"] + values["unknown"],
                metadata=trace,
            )

    utility = FearOverrideUtility()
    frame = utility.evaluate(
        perception=Perception(
            id="perception-fear-override",
            actor_id="actor-1",
            source_id="world-1",
            context={"known": 2.0},
        ),
        actor=Actor(id="actor-1"),
        context={
            "missing_metric_policy": "default_pessimistic",
            "missing_metric_default": -3.5,
        },
    )

    assert frame.value == -1.5
    assert frame.metadata["missing_metric_policy"] == "default_pessimistic"
    assert frame.metadata["missing_metric_default"] == -3.5
    assert frame.metadata["missing_metrics"] == ["unknown"]
    assert frame.metadata["metric_sources"]["unknown"] == "default_missing"


def test_utility_function_resolve_numeric_metrics_strict_invalid_raises():
    """Strict invalid mode raises instead of silently applying fallback."""

    class StrictPolicyUtility(UtilityFunction):
        @property
        def framework_id(self) -> str:
            return "strict-framework"

        @property
        def is_multi_criteria(self) -> bool:
            return False

        def evaluate(self, perception, actor, context):
            del actor
            values, trace = self.resolve_numeric_metrics(
                ["known", "bad"],
                perception=perception,
                context=context,
            )
            return self.build_utility_frame(value=values["known"], metadata=trace)

    utility = StrictPolicyUtility()
    with pytest.raises(ValueError, match="non-numeric value"):
        utility.evaluate(
            perception=Perception(
                id="perception-strict-invalid",
                actor_id="actor-1",
                source_id="world-1",
                context={"known": 1.0, "bad": "not-numeric"},
            ),
            actor=Actor(id="actor-1"),
            context={"missing_metric_strict_invalid": True},
        )


def test_utility_function_resolve_numeric_metrics_exposes_fallback_dominance_flag():
    """Metadata flags when fallback usage dominates under configured threshold."""

    class DominanceUtility(UtilityFunction):
        @property
        def framework_id(self) -> str:
            return "dominance-framework"

        @property
        def is_multi_criteria(self) -> bool:
            return False

        def evaluate(self, perception, actor, context):
            del actor
            values, trace = self.resolve_numeric_metrics(
                ["k1", "k2", "k3", "k4"],
                perception=perception,
                context=context,
            )
            return self.build_utility_frame(value=sum(values.values()), metadata=trace)

    utility = DominanceUtility()
    frame = utility.evaluate(
        perception=Perception(
            id="perception-dominance",
            actor_id="actor-1",
            source_id="world-1",
            context={"k1": 1.0},
        ),
        actor=Actor(id="actor-1"),
        context={"fallback_dominance_threshold": 0.49},
    )

    assert frame.metadata["fallback_applied_count"] == 3
    assert frame.metadata["total_metrics"] == 4
    assert frame.metadata["fallback_ratio"] == 0.75
    assert frame.metadata["fallback_dominance_threshold"] == 0.49
    assert frame.metadata["fallback_dominates"] is True


def test_utility_function_build_utility_frame_adds_standard_metadata():
    """Utility frame helper always injects framework and utility shape metadata."""

    class BuilderUtility(UtilityFunction):
        @property
        def framework_id(self) -> str:
            return "builder-framework"

        @property
        def is_multi_criteria(self) -> bool:
            return True

        def evaluate(self, perception, actor, context):
            del perception, actor, context
            return self.build_utility_frame(
                value=[1.0, 2.0],
                criteria_labels=["a", "b"],
                metadata={"note": "custom"},
            )

    utility = BuilderUtility()
    frame = utility.evaluate(
        perception=Perception(
            id="perception-builder",
            actor_id="actor-1",
            source_id="world-1",
        ),
        actor=Actor(id="actor-1"),
        context={},
    )

    assert frame.framework_id == "builder-framework"
    assert frame.metadata["framework_id"] == "builder-framework"
    assert frame.metadata["utility_shape"] == "vector"
    assert frame.metadata["note"] == "custom"
