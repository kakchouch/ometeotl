"""Tests for model interface exports required by F-26."""

from ometeotl_core.model import (
    ContextualBuildable,
    LLMExportable,
    Serializable,
    Validatable,
)


def test_f26_interface_symbols_are_exported():
    """The model package exposes the required interface symbols."""
    assert Serializable is not None
    assert Validatable is not None
    assert LLMExportable is not None
    assert ContextualBuildable is not None
