from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_fun006880c0_request_object_identity.json"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_fun006880c0_request_object_identity.py"
DOC = ROOT / "docs/PROCESS_1_FUN006880C0_REQUEST_OBJECT_IDENTITY.md"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("process1_fun006880c0_request_identity", ANALYZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fun006880c0_source_visible_direct_surface_is_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Process1Fun006880c0RequestObjectIdentity/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["upstream_contract"] == "SHIFT.Process1Fun006880c0QueueProvenance/1"
    assert payload["source"]["xbox_recomp_required"] is False

    surface = payload["source_visible_request_surface"]
    assert surface["fun_00634ed0"]["call_count"] == 2
    assert surface["fun_00634ed0"]["request_object"] == "owner+0x1820"
    assert surface["fun_00634f00"]["call_count"] == 3
    assert surface["fun_00634f00"]["embedded_request_count"] == 2
    assert surface["fun_00634f00"]["heap_request_count"] == 1
    assert surface["fun_00634f00"]["heap_request_size"] == "0x220"
    assert surface["fun_00634f50"]["call_count"] == 20
    assert surface["fun_00634f50"]["direct_embedded_request_offsets"] == [
        "+0x100",
        "+0x120",
        "+0x140",
        "+0x160",
    ]

    adjudication = payload["adjudication"]
    assert adjudication["fun_006880c0_source_visible_direct_surface_closed"] is True
    assert adjudication["fun_006880c0_controller1_queue_alias_ruled_out_for_direct_surface"] is True
    assert adjudication["fun_006333f0_controller1_alias_ruled_out"] is False
    assert adjudication["indirect_or_native_apc_injection_ruled_out"] is False
    assert adjudication["render_or_present_phase_lock_proven"] is False
    assert payload["next_blocker"]["remaining_generic_queue_pointer_callers"] == [
        "FUN_006333f0"
    ]


def test_analyzer_locks_request_object_surface_shape() -> None:
    module = load_analyzer()
    assert module.SOURCE_SHA256 == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert module.UPSTREAM_CONTRACT == "SHIFT.Process1Fun006880c0QueueProvenance/1"
    assert module.API_WRAPPERS == ["FUN_00634ed0", "FUN_00634f00", "FUN_00634f50"]
    assert module.F50_EMBEDDED_OFFSETS == ["0x100", "0x120", "0x140", "0x160"]


def test_documentation_keeps_non_direct_wake_paths_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "source-visible direct call surface" in text
    assert "operation/request object" in text
    assert "not the recovered Controller #1 queue object" in text
    assert "does **not** claim" in text
    assert "native APC" in text
    assert "does not prove render/presentation phase locking" in text
    assert "`FUN_006333f0`" in text
    assert "Xbox 360 recomp" in text
    assert "not required for any promoted claim" in text
