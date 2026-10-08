from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_lobbyclient_embedded_queue_owner.json"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_lobbyclient_embedded_queue_owner.py"
DOC = ROOT / "docs/PROCESS_1_LOBBYCLIENT_EMBEDDED_QUEUE_OWNER.md"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("process1_lobbyclient_embedded_owner", ANALYZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_embedded_queue_owner_closes_fun_006503d0_direct_surface() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Process1LobbyClientEmbeddedQueueOwner/1"
    assert payload["ready"] is True
    assert payload["owner"]["diagnostic_name"] == "Plasma_Online"
    assert payload["owner"]["queue_name"] == "LobbyClient Output Message Queue"
    assert payload["owner"]["queue_offset"] == "+0x2180"
    assert payload["owner"]["derived_vtable"] == "0x00ad96d8"
    assert payload["owner"]["embedded_method_vtable_slot"] == "+0x2a0"
    assert payload["owner"]["embedded_method"] == "FUN_005a8b90"
    assert payload["fun_006503d0"]["direct_callsite_count"] == 3
    assert payload["fun_006503d0"]["all_direct_callers_joined_to_lobby_client"] is True
    assert payload["fun_006503d0"]["controller1_queue_alias_ruled_out_for_direct_call_surface"] is True
    assert payload["adjudication"]["fun_006503d0_direct_surface_closed"] is True
    assert payload["adjudication"]["fun_006333f0_controller1_alias_ruled_out"] is False
    assert payload["adjudication"]["fun_006880c0_controller1_alias_ruled_out"] is False
    assert payload["adjudication"]["indirect_or_native_apc_injection_ruled_out"] is False
    assert payload["adjudication"]["render_or_present_phase_lock_proven"] is False
    assert payload["next_blocker"]["remaining_generic_queue_pointer_callers"] == [
        "FUN_006333f0",
        "FUN_006880c0",
    ]


def test_analyzer_pins_derived_vtable_and_enqueue_callsite() -> None:
    module = load_analyzer()
    assert module.DERIVED_VTABLE == 0x00AD96D8
    assert module.EMBEDDED_METHOD_SLOT == 0x2A0
    assert module.DERIVED_VTABLE + module.EMBEDDED_METHOD_SLOT == 0x00AD9978
    assert module.EMBEDDED_METHOD == 0x005A8B90
    assert module.QUEUE_OFFSET == 0x2180
    assert module.SPANS["derived_vptr_store_and_tail_jump"][:2] == (
        0x0047F69C,
        0x0047F6A7,
    )
    assert module.SPANS["embedded_method_vtable_slot"][:2] == (
        0x00AD9978,
        0x00AD997C,
    )
    assert module.SPANS["embedded_method_enqueue_call"][:2] == (
        0x005A8C13,
        0x005A8C23,
    )


def test_documentation_keeps_remaining_wake_surface_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "all three direct callers" in text
    assert "cannot be the recovered Controller #1 queue" in text
    assert "`FUN_006333f0`" in text
    assert "`FUN_006880c0`" in text
    assert "does not rule out dynamically populated or native APC injection" in text
    assert "does not prove render/presentation phase locking" in text
    assert "all positive claims are PC-backed" in text
