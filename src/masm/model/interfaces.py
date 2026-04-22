"""Core abstract interfaces required by the model architecture.

These protocols provide minimal contracts for cross-layer interoperability
without forcing concrete inheritance.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Self


class Serializable(Protocol):
    """Object that can be serialized to and reconstructed from mapping data."""

    def to_dict(self) -> dict[str, Any]:
        """Return canonical dictionary serialization."""
        ...

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Self:
        """Rebuild an instance from canonical mapping data."""
        ...


class Validatable(Protocol):
    """Object that can expose a validation hook."""

    def validate(self, context: Mapping[str, Any] | None = None) -> Any:
        """Validate the object using optional contextual information."""
        ...


class LLMExportable(Protocol):
    """Object that can provide a language-model-oriented representation."""

    def to_llm_view(self) -> Mapping[str, Any]:
        """Return a view tailored for language-model consumption."""
        ...


class ContextualBuildable(Protocol):
    """Object that can be built from context rather than canonical payload."""

    @classmethod
    def from_context(cls, context: Mapping[str, Any]) -> Self:
        """Construct an instance from contextual data."""
        ...
