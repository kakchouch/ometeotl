"""Canonical export helpers for the IO layer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from masm.model.base import JsonMap, _deep_plain_copy
from masm.model.world import World


def world_to_mapping(world: World) -> JsonMap:
    """Return the canonical mapping payload for a world."""
    return _deep_plain_copy(world.to_dict())


def world_to_json(world: World, *, indent: int = 2) -> str:
    """Serialize a world to deterministic JSON text."""
    return json.dumps(
        world_to_mapping(world),
        indent=indent,
        sort_keys=True,
    )


def world_to_yaml(world: World) -> str:
    """Serialize a world to deterministic YAML text."""
    return yaml.safe_dump(
        world_to_mapping(world),
        allow_unicode=False,
        sort_keys=True,
    )


def write_world_json(world: World, path: str | Path, *, indent: int = 2) -> Path:
    """Write a deterministic JSON export for a world."""
    output_path = Path(path)
    output_path.write_text(world_to_json(world, indent=indent), encoding="utf-8")
    return output_path


def write_world_yaml(world: World, path: str | Path) -> Path:
    """Write a deterministic YAML export for a world."""
    output_path = Path(path)
    output_path.write_text(world_to_yaml(world), encoding="utf-8")
    return output_path
