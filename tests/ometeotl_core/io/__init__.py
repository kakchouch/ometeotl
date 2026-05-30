"""Test package compatibility helpers for the world IO test suite.

Pytest can place this package on ``sys.path`` in a way that shadows the
standard library ``io`` module. That breaks third-party imports that rely on
``io.StringIO``. We mirror the stdlib module attributes here so the test
package stays harmless if it is imported as top-level ``io`` during test
collection.
"""

from __future__ import annotations

import importlib.util
import sysconfig
from pathlib import Path


def _load_stdlib_io() -> object:
	stdlib_path = Path(sysconfig.get_path("stdlib")) / "io.py"
	spec = importlib.util.spec_from_file_location("_stdlib_io", stdlib_path)
	if spec is None or spec.loader is None:
		raise ImportError(f"Unable to load stdlib io module from {stdlib_path}")

	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


_stdlib_io = _load_stdlib_io()

for _name in dir(_stdlib_io):
	if not _name.startswith("_"):
		globals()[_name] = getattr(_stdlib_io, _name)

