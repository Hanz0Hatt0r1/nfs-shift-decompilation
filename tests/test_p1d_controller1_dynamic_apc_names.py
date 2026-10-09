from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1d_controller1_dynamic_apc_names.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1d_dynamic_apc_names", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_find_embedded_names_detects_ascii_and_utf16() -> None:
    tool = load_tool()
    data = (
        b"prefix\0QueueUserAPC\0middle\0"
        + "NtQueueApcThreadEx".encode("utf-16le")
        + b"\0\0suffix"
    )
    found = tool.find_embedded_names(data, ("QueueUserAPC", "NtQueueApcThreadEx", "Missing"))
    assert found == {
        "QueueUserAPC": ["ascii-nul"],
        "NtQueueApcThreadEx": ["utf16le-nul"],
    }


def test_empty_plain_name_surface_does_not_become_universal_no_apc() -> None:
    tool = load_tool()
    payload = tool.build_payload(
        imports={"GetProcAddress": {"iat_va": "0x1"}},
        embedded_names={},
    )
    a = payload["adjudication"]
    assert a["plain_name_dynamic_resolution_surface_empty"] is True
    assert a["plain_name_dynamic_resolution_surface_is_universal_no_apc_proof"] is False
    assert a["hashed_or_generated_api_name_resolution_ruled_out"] is False
    assert a["manual_syscall_or_native_injection_ruled_out"] is False
    assert a["indirect_or_native_apc_injection_ruled_out"] is False
    assert a["controller1_timing_exhaustive"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7


def test_nonempty_resolver_and_name_surface_stays_candidate_only() -> None:
    tool = load_tool()
    payload = tool.build_payload(
        imports={
            "GetProcAddress": {"iat_va": "0x00aa0000"},
            "QueueUserAPC": {"iat_va": "0x00aa0004"},
        },
        embedded_names={"QueueUserAPC": ["ascii-nul"]},
    )
    assert payload["dynamic_resolver_imports_present"] == ["GetProcAddress"]
    assert payload["direct_apc_injection_imports_present"] == ["QueueUserAPC"]
    assert payload["embedded_apc_api_names"] == {"QueueUserAPC": ["ascii-nul"]}
    assert payload["adjudication"]["plain_name_dynamic_resolution_surface_empty"] is False
    assert payload["adjudication"]["indirect_or_native_apc_injection_ruled_out"] is False


def test_target_sets_cover_user_and_native_apc_families() -> None:
    tool = load_tool()
    assert "QueueUserAPC" in tool.APC_NAMES
    assert "NtQueueApcThread" in tool.APC_NAMES
    assert "NtQueueApcThreadEx" in tool.APC_NAMES
    assert "ZwQueueApcThread" in tool.APC_NAMES
    assert "RtlQueueApcWow64Thread" in tool.APC_NAMES
    assert "SetWaitableTimerEx" in tool.APC_NAMES
    assert "GetProcAddress" in tool.RESOLVER_NAMES
    assert "LdrGetProcedureAddress" in tool.RESOLVER_NAMES
