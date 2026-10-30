"""CI entry points for the Xbox 360 Process 1 GPU dispatch trace regressions."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_tool_test(filename: str, module_name: str):
    path = Path(__file__).parents[1] / "tools" / "xbox360" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_DISPATCH_ID_TEST = _load_tool_test(
    "test_linux_gpu_dispatch_id_trace_contract_20261028.py",
    "process1_gpu_dispatch_id_trace_contract",
)
_JOIN_TEST = _load_tool_test(
    "test_join_linux_source1_gpu_dispatches_20261028.py",
    "process1_source1_gpu_dispatch_join",
)


def test_gpu_dispatch_id_correlation_contract() -> None:
    _DISPATCH_ID_TEST.main()


def test_source1_gpu_dispatch_join() -> None:
    _JOIN_TEST.main()
