from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_lobbyclient_queue_aliases.json"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_lobbyclient_queue_aliases.py"
DOC = ROOT / "docs/PROCESS_1_LOBBYCLIENT_QUEUE_ALIASES.md"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("process1_lobbyclient_aliases", ANALYZER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lobbyclient_queue_alias_evidence_narrows_controller1_frontier() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.Process1LobbyClientQueueAliases/1"
    assert payload["ready"] is True
    assert payload["lobby_client"]["owner_name"] == "Plasma_Online"
    assert payload["lobby_client"]["queue_name"] == "LobbyClient Output Message Queue"
    assert payload["lobby_client"]["queue_offset"] == "+0x2180"
    assert payload["lobby_client"]["queue_accessor_vtable_slot"] == "+0x88"
    assert payload["lobby_client"]["queue_accessor"] == "0x005aa4e0"
    assert payload["adjudication"]["fun_0057e5b0_controller1_queue_alias_ruled_out"] is True
    assert payload["adjudication"]["fun_0057e820_controller1_queue_alias_ruled_out"] is True
    assert payload["adjudication"]["fun_006503d0_two_of_three_direct_calls_joined_to_lobby_client"] is True
    assert payload["adjudication"]["fun_006503d0_all_possible_controller1_aliases_ruled_out"] is False
    assert payload["adjudication"]["indirect_or_native_apc_injection_ruled_out"] is False
    assert payload["adjudication"]["render_or_present_phase_lock_proven"] is False
    assert payload["next_blocker"]["remaining_generic_queue_pointer_callers"] == [
        "FUN_006333f0",
        "FUN_006503d0",
        "FUN_006880c0",
    ]


def test_lobbyclient_queue_alias_analyzer_pins_machine_identity() -> None:
    module = load_analyzer()
    assert module.LOBBY_VTABLE == 0x00AE3B00
    assert module.LOBBY_QUEUE_VTABLE_SLOT == 0x88
    assert module.LOBBY_QUEUE_ACCESSOR == 0x005AA4E0
    assert module.LOBBY_QUEUE_OFFSET == 0x2180
    assert module.SPANS["lobby_queue_accessor"][:2] == (0x005AA4E0, 0x005AA4E7)
    assert module.SPANS["lobby_vtable_queue_slot"][:2] == (0x00AE3B88, 0x00AE3B8C)


def test_lobbyclient_queue_alias_documentation_stays_fail_closed() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "machine-proven to return `this+0x2180`" in text
    assert "cannot be the recovered Controller #1 queue" in text
    assert "does not promote its exact owner type" in text
    assert "indirect/native APC injection" in text
    assert "render/presentation phase locking" in text
