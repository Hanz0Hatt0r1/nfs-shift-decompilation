import json
from pathlib import Path

EVIDENCE = Path("evidence/p1d_controller1_apc_sqlite_result.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_source_index_and_counts_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1D.Controller1ApcSqliteResult/1"
    assert data["authority"]["source_index_format"] == "SHIFT.GhidraSQLiteIndex/1"
    assert data["authority"]["source_index_sha256"] == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert data["index_counts"] == {"functions": 41538, "calls": 200598, "strings": 53433}


def test_getprocaddress_surface_is_real_but_target_names_are_absent():
    data = load_evidence()
    assert data["getprocaddress"]["direct_call_count"] == 100
    assert data["getprocaddress"]["unique_caller_count"] == 18
    assert len(data["getprocaddress"]["unique_callers"]) == 18
    assert data["exact_embedded_target_name_rows"] == {}
    a = data["adjudication"]
    assert a["getprocaddress_surface_present"] is True
    assert a["plain_target_api_names_present_in_index"] is False
    assert a["plain_name_apc_resolution_supported_by_sqlite_index"] is False


def test_openal_queue_strings_are_not_promoted_to_apc_semantics():
    rows = load_evidence()["resolver_caller_suspicious_strings"]
    assert [(row["caller"], row["value"]) for row in rows] == [
        ("0x009a7e04", "alSourceUnqueueBuffers"),
        ("0x009a7e04", "alSourceQueueBuffers"),
    ]


def test_fail_closed_apc_gates_remain_open():
    a = load_evidence()["adjudication"]
    assert a["hashed_or_generated_resolution_ruled_out"] is False
    assert a["manual_export_walk_ruled_out"] is False
    assert a["native_or_syscall_injection_ruled_out"] is False
    assert a["controller1_timing_exhaustive"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7
