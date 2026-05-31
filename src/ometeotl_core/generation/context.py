"""Generation context primitives for ometeotl_core.

The generation layer stays intentionally lightweight: it defines a
small, structured context object that can be turned into model objects by the
pipeline without pushing business logic into the model layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class GenerationPlacement:
    """Explicit placement instruction used when generating a world."""

    object_id: str
    space_id: str
    role: str = "occupies"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "space_id": self.space_id,
            "role": self.role,
            "metadata": dict(self.metadata),
        }


@dataclass
class GenerationContext:
    """Declarative input used to generate one model object."""

    kind: str
    id: str
    label: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    relations: dict[str, list[str]] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    spaces: list["GenerationContext"] = field(default_factory=list)
    actors: list["GenerationContext"] = field(default_factory=list)
    resources: list["GenerationContext"] = field(default_factory=list)
    goals: list["GenerationContext"] = field(default_factory=list)
    strategies: list["GenerationContext"] = field(default_factory=list)
    actions: list["GenerationContext"] = field(default_factory=list)
    placements: list[GenerationPlacement] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    validate: bool = False
    validation_mode: str = "lenient"
    stage_modes: dict[str, str] = field(default_factory=dict)

    def child_collections(self) -> dict[str, list["GenerationContext"]]:
        """Return the nested context collections in one stable mapping."""
        return {
            "spaces": list(self.spaces),
            "actors": list(self.actors),
            "resources": list(self.resources),
            "goals": list(self.goals),
            "strategies": list(self.strategies),
            "actions": list(self.actions),
        }

    def merged_attributes(self) -> dict[str, Any]:
        """Return attributes with the label promoted when present."""
        merged = dict(self.attributes)
        if self.label and "label" not in merged:
            merged["label"] = self.label
        return merged

    def merged_context(self) -> dict[str, Any]:
        """Return context metadata enriched with the generation payload."""
        merged = dict(self.context)
        if self.metadata:
            merged.setdefault("generation", {})
            generation_metadata = dict(merged["generation"])
            generation_metadata.update(self.metadata)
            merged["generation"] = generation_metadata
        return merged

    def normalized_relations(self) -> dict[str, list[str]]:
        """Return deterministic relation lists with duplicates removed."""
        normalized: dict[str, list[str]] = {}
        for key, values in self.relations.items():
            normalized[key] = sorted({str(value) for value in values if value})
        return normalized

    def copy_with(self, **changes: Any) -> "GenerationContext":
        """Return a modified copy of this generation context."""
        data = {
            "kind": self.kind,
            "id": self.id,
            "label": self.label,
            "attributes": dict(self.attributes),
            "relations": dict(self.relations),
            "state": dict(self.state),
            "context": dict(self.context),
            "provenance": dict(self.provenance),
            "spaces": list(self.spaces),
            "actors": list(self.actors),
            "resources": list(self.resources),
            "goals": list(self.goals),
            "strategies": list(self.strategies),
            "actions": list(self.actions),
            "placements": list(self.placements),
            "metadata": dict(self.metadata),
            "validate": self.validate,
            "validation_mode": self.validation_mode,
            "stage_modes": dict(self.stage_modes),
        }
        data.update(changes)
        return GenerationContext(**data)
