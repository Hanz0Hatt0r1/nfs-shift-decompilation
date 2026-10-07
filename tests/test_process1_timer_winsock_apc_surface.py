from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/process1_timer_winsock_apc_surface.json"
DOC = ROOT / "docs/PROCESS_1_TIMER_WINSOCK_APC_SURFACE.md"
ANALYZER = ROOT / "tools/ghidra/analyze_process1_timer_winsock_apc_surface.py"


def load_evidence() -> dict[str, object]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_process1_timer_winsock_apc_evidence_is_hash_locked() -> None:
    payload = load_evidence()
    source = payload["source"]
    assert payload["format"] == "SHIFT.Process1TimerWinsockApcSurface/1"
    assert payload["ready"] is True
    assert source["authority"] == "PC retail 1.02"
    assert source["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert source["retail_executable_sha256"] == (
        "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    )
    assert source["retail_source_sha256"] == (
        "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    )
    assert source["xbox_recomp_required"] is False

    expected_hashes = {
        "winsock_recv_completion_null": "5eaa9132ff21897e6d6ee6c59b3195acf654a4646ad91e25b22a0be792376704",
        "wsaioctl_overlapped_and_completion_null": "8ce632ff7491eda26149922a41f554df18bf56973326019ff4c16f9affa65f93",
        "fmod_record_timer_completion_null": "a0a0e4ead543d84609f384412cfd8a83e828715255357d9db0794caacb972cc4",
        "fmod_output_timer_completion_null": "931ce092f2f87cc190ab97aa57cea7dd34fb7b53abb69826464738902519e702",
    }
    spans = payload["machine_spans"]
    assert {name: value["sha256"] for name, value in spans.items()} == expected_hashes


def test_timer_completion_routines_are_disabled() -> None:
    payload = load_evidence()
    surface = payload["timer_completion_surface"]
    assert surface["api"] == "SetWaitableTimer"
    assert surface["physical_machine_callsite_count"] == 2
    assert surface["ghidra_source_rendered_call_count"] == 3
    assert surface["completion_routine_nonnull_callsite_count"] == 0
    assert surface["completion_argument_nonnull_callsite_count"] == 0
    assert {entry["owner"] for entry in surface["callsites"]} == {
        "FUN_009983fe",
        "FUN_00998936",
    }
    for entry in surface["callsites"]:
        assert entry["pfnCompletionRoutine"] == "NULL"
        assert entry["lpArgToCompletionRoutine"] == "NULL"
        assert entry["fResume"] is False


def test_winsock_completion_routines_are_disabled() -> None:
    payload = load_evidence()
    surface = payload["winsock_completion_surface"]
    assert surface["owner_recv"] == "FUN_005fdc90"
    assert surface["owner_ioctl"] == "FUN_005ff390"
    assert surface["wsarecv_completion_routine"] == "NULL"
    assert surface["wsarecvfrom_completion_routine"] == "NULL (machine ABI ninth argument)"
    assert surface["wsaioctl_overlapped"] == "NULL"
    assert surface["wsaioctl_completion_routine"] == "NULL"

    adjudication = payload["adjudication"]
    assert adjudication["source_visible_waitable_timer_completion_can_apc_controller1"] is False
    assert adjudication["source_visible_winsock_completion_can_apc_controller1"] is False
    assert adjudication["timer_and_winsock_completion_callbacks_are_not_controller1_wake_sources"] is True


def test_negative_surface_keeps_indirect_and_file_apc_scope_fail_closed() -> None:
    payload = load_evidence()
    adjudication = payload["adjudication"]
    assert adjudication["readfileex_writefileex_surface_adjudicated_here"] is False
    assert adjudication["indirect_or_native_apc_sources_ruled_out"] is False
    assert adjudication["render_or_present_phase_lock_proven"] is False
    assert payload["next_blocker"]["process"] == 1

    doc = DOC.read_text(encoding="utf-8")
    assert "bounded negative result" in doc
    assert "does **not** adjudicate" in doc
    assert "does not rule out undocumented/native or indirect APC queueing" in doc


def test_analyzer_rejects_retail_identity_or_completion_drift() -> None:
    source = ANALYZER.read_text(encoding="utf-8")
    assert 'SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"' in source
    assert 'EXE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"' in source
    assert 'EXE_SHA256 = "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"' in source
    assert '"QueueUserAPC" in text' in source
    assert '"WSAIoctl null overlapped/completion push pattern drift"' in source
    assert '"record timer zero-argument push pattern drift"' in source
    assert '"output timer zero-argument push pattern drift"' in source
