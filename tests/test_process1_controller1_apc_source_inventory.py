from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_controller1_apc_source_inventory.json"
DOC = ROOT / "docs/PROCESS_1_CONTROLLER1_APC_SOURCE_INVENTORY.md"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_controller1_apc_source_inventory.py"


def load_evidence() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_apc_source_inventory_is_exact_and_pc_authoritative() -> None:
    payload = load_evidence()
    assert payload["format"] == "SHIFT.Process1Controller1ApcSourceInventory/1"
    assert payload["ready"] is True
    assert payload["source"]["authority"] == "PC retail 1.02"
    assert payload["source"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert payload["source"]["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert payload["imported_completion_apc_surface"]["imports"] == {
        "SetWaitableTimer": "0x00aa6108",
        "WriteFileEx": "0x00aa6234",
        "ReadFileEx": "0x00aa6240",
        "WSARecvFrom": "0x00aa64e8",
        "WSARecv": "0x00aa64ec",
        "WSAIoctl": "0x00aa6524",
    }
    assert payload["imported_completion_apc_surface"]["direct_apc_injection_imports_present"] == []


def test_completion_surface_has_no_concrete_controller1_owner() -> None:
    payload = load_evidence()
    ownership = payload["ownership_join"]
    assert ownership["ReadFileEx"] == "Base File: Async Thread"
    assert ownership["WriteFileEx"] == "Base File: Async Thread"
    assert "NULL" in ownership["SetWaitableTimer"]
    assert ownership["WSARecv"] == "completion routine NULL"
    assert ownership["WSARecvFrom"] == "completion routine NULL"
    assert "completion routine NULL" in ownership["WSAIoctl"]

    controller = payload["controller1"]
    assert controller["worker"] == "FUN_00662880"
    assert controller["alertable_sleep"] == "SleepEx(10, TRUE)"
    assert controller["concrete_imported_completion_source_joined_to_controller1"] is False
    assert controller["direct_named_manager_path_to_readfileex_or_writefileex"] is False


def test_join_stays_fail_closed_for_indirect_or_native_apc() -> None:
    payload = load_evidence()
    adjudication = payload["adjudication"]
    assert adjudication["known_imported_completion_apc_sources_accounted_for"] is True
    assert adjudication["known_imported_completion_apc_source_targets_controller1_proven"] is False
    assert adjudication["controller1_alertable_sleep_has_concrete_recovered_apc_wake_source_proven"] is False
    assert adjudication["indirect_or_native_apc_injection_ruled_out"] is False
    assert adjudication["render_or_present_phase_lock_proven"] is False
    assert payload["next_blocker"]["process"] == 1

    doc = DOC.read_text(encoding="utf-8")
    assert "not a universal no-APC theorem" in doc
    assert "undocumented/native APC injection" in doc
    assert "does not prove render/presentation phase locking" in doc


def test_analyzer_parses_pe_imports_and_requires_prior_contracts() -> None:
    source = ANALYZER.read_text(encoding="utf-8")
    assert '"SetWaitableTimer": "0x00aa6108"' in source
    assert '"ReadFileEx": "0x00aa6240"' in source
    assert '"WSARecv": "0x00aa64ec"' in source
    assert '"QueueUserAPC"' in source
    assert '"SHIFT.Process1AsyncFileApcOwnership/1"' in source
    assert '"SHIFT.Process1TimerWinsockApcSurface/1"' in source
    assert '"SHIFT.Process1Controller1ManagerApcReachability/1"' in source
    assert 'raise ValueError(f"APC-capable import surface drift: {recovered!r}")' in source
