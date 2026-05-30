"""Test package compatibility helpers for the world IO test suite.

Pytest can place this package on ``sys.path`` in a way that shadows the
standard library ``io`` module. That breaks third-party imports that rely on
``io.StringIO``. We mirror the stdlib module attributes here so the test
package stays harmless if it is imported as top-level ``io`` during test
collection.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _load_stdlib_io() -> object:
	original_path = list(sys.path)
	original_io = sys.modules.pop("io", None)

	tests_root = Path(__file__).resolve().parents[3]

	try:
		sys.path = [
			path
			for path in original_path
			if path and tests_root.as_posix() not in Path(path).as_posix()
		]
		return importlib.import_module("io")
	finally:
		sys.path = original_path
		if original_io is not None:
			sys.modules["io"] = original_io


_stdlib_io = _load_stdlib_io()

for _name in dir(_stdlib_io):
	if not _name.startswith("_"):
		globals()[_name] = getattr(_stdlib_io, _name)

