"""Tests for abstract space behavior in masm.model.spaces."""

import pytest

from masm.model.spaces import Space


def test_space_is_abstract_defaults_false():
    """Space.is_abstract should default to False."""
    space = Space(id="space-1")
    assert space.is_abstract is False


def test_space_is_abstract_setter():
    """Space.is_abstract can be set to True."""
    space = Space(id="space-1")
    space.is_abstract = True
    assert space.is_abstract is True
    space.is_abstract = False
    assert space.is_abstract is False


def test_space_serialization_round_trip_with_is_abstract():
    """Space serializes and reconstructs with is_abstract attribute."""
    space = Space(id="space-abstract")
    space.is_abstract = True
    space.kind = "conceptual"

    restored = Space.from_dict(space.to_dict())

    assert restored.is_abstract is True
    assert restored.kind == "conceptual"
