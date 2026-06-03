"""Global pytest hooks for export audit artifact capture.

This test hook records serialization/export outputs so they can be audited under
local_lab/artifacts without changing each test individually.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import pkgutil
import re
from collections import defaultdict
from typing import Any, Callable

import pytest

from tests.ometeotl_core._artifact_utils import (
    write_json_artifact,
    write_text_artifact,
)

_CURRENT_TEST_NODEID = ""
_LAYER_COUNTERS: defaultdict[str, int] = defaultdict(int)


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()


def _safe_write_json(*, layer: str, name: str, payload: Any) -> None:
    try:
        write_json_artifact(layer=layer, name=name, payload=payload)
    except Exception as exc:  # pragma: no cover - never break tests on audit write
        write_json_artifact(
            layer=layer,
            name=f"{name}_fallback",
            payload={
                "error": str(exc),
                "payload_repr": repr(payload),
            },
        )


def _record_json_artifact(*, layer: str, label: str, payload: Any) -> None:
    if not _CURRENT_TEST_NODEID:
        return
    _LAYER_COUNTERS[layer] += 1
    counter = _LAYER_COUNTERS[layer]
    name = f"{_slug(_CURRENT_TEST_NODEID)}__{_slug(label)}__{counter:03d}"
    _safe_write_json(layer=layer, name=name, payload=payload)


def _record_text_artifact(
    *, layer: str, label: str, content: str, extension: str
) -> None:
    if not _CURRENT_TEST_NODEID:
        return
    _LAYER_COUNTERS[layer] += 1
    counter = _LAYER_COUNTERS[layer]
    name = f"{_slug(_CURRENT_TEST_NODEID)}__{_slug(label)}__{counter:03d}"
    try:
        write_text_artifact(
            layer=layer,
            name=name,
            content=content,
            extension=extension,
        )
    except Exception:
        # Artifact writes must stay observational and never impact test behavior.
        pass


def _wrap_method(cls: type[Any], method_name: str, layer: str) -> None:
    method = getattr(cls, method_name, None)
    if method is None or not callable(method):
        return
    if getattr(method, "__ometeotl_audit_wrapped__", False):
        return

    @functools.wraps(method)
    def wrapped(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = method(self, *args, **kwargs)
        _record_json_artifact(
            layer=layer,
            label=f"{cls.__name__}_{method_name}",
            payload=result,
        )
        return result

    setattr(wrapped, "__ometeotl_audit_wrapped__", True)
    setattr(cls, method_name, wrapped)


def _wrap_function(module: Any, function_name: str, layer: str, extension: str) -> None:
    function = getattr(module, function_name, None)
    if function is None or not callable(function):
        return
    if getattr(function, "__ometeotl_audit_wrapped__", False):
        return

    @functools.wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        result = function(*args, **kwargs)
        if extension == "json":
            _record_text_artifact(
                layer=layer,
                label=function_name,
                content=str(result),
                extension="json",
            )
        elif extension == "yaml":
            _record_text_artifact(
                layer=layer,
                label=function_name,
                content=str(result),
                extension="yaml",
            )
        else:
            _record_json_artifact(
                layer=layer,
                label=function_name,
                payload=result,
            )
        return result

    setattr(wrapped, "__ometeotl_audit_wrapped__", True)
    setattr(module, function_name, wrapped)


def _install_model_export_wrappers() -> None:
    model_pkg = importlib.import_module("ometeotl_core.model")

    for module_info in pkgutil.walk_packages(
        model_pkg.__path__, model_pkg.__name__ + "."
    ):
        module = importlib.import_module(module_info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__:
                continue
            _wrap_method(cls, "to_dict", "exports/model/to_dict")
            _wrap_method(cls, "to_llm_view", "exports/model/to_llm_view")


def _install_io_export_wrappers() -> None:
    io_module = importlib.import_module("ometeotl_core.io")
    _wrap_function(io_module, "world_to_json", "exports/io/world_to_json", "json")
    _wrap_function(io_module, "world_to_yaml", "exports/io/world_to_yaml", "yaml")
    _wrap_function(
        io_module, "world_to_llm_view", "exports/io/world_to_llm_view", "dict"
    )


_install_model_export_wrappers()
_install_io_export_wrappers()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    global _CURRENT_TEST_NODEID

    _CURRENT_TEST_NODEID = item.nodeid
    _LAYER_COUNTERS.clear()
    yield
    _CURRENT_TEST_NODEID = ""
