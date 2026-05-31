"""Helpers for writing local test artifacts under local_lab.

Artifacts are intentionally written outside tracked source folders to keep
audit snapshots accessible without polluting the repository history.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_text_artifact(
    *,
    layer: str,
    name: str,
    content: str,
    extension: str,
) -> Path:
    """Write one text artifact under local_lab/artifacts/<layer>/.

    The output filename is stable and is overwritten on each run to avoid
    data accumulation.
    """
    repo_root = Path(__file__).resolve().parents[2]
    artifact_dir = repo_root / "local_lab" / "artifacts" / layer
    artifact_dir.mkdir(parents=True, exist_ok=True)

    normalized_extension = extension.lstrip(".")
    artifact_path = artifact_dir / f"{name}.{normalized_extension}"
    artifact_path.write_text(content, encoding="utf-8")
    return artifact_path


def write_json_artifact(*, layer: str, name: str, payload: Any) -> Path:
    """Write one JSON artifact under local_lab/artifacts/<layer>/.

    The output filename is stable and is overwritten on each run to avoid
    data accumulation.
    """
    return write_text_artifact(
        layer=layer,
        name=name,
        content=json.dumps(payload, indent=2, sort_keys=True) + "\n",
        extension="json",
    )
