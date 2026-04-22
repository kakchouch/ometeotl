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


def test_utility_function_incomplete_subclass_rejected():
    """UtilityFunction subclass missing abstract methods raises on instantiation."""

    class IncompleteUtility(UtilityFunction):
        """Missing framework_id, is_multi_criteria, and evaluate implementations."""

        pass

    with pytest.raises(TypeError):
        IncompleteUtility()


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
