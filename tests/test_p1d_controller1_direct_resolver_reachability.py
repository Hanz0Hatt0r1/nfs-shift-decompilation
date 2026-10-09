import json
from pathlib import Path

EVIDENCE = Path("evidence/p1d_controller1_direct_resolver_reachability.json")


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_worker_and_resolver_counts_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1D.Controller1DirectResolverReachability/1"
    assert data["worker"] == "0x00662880"
    surface = data["resolver_surface"]
    assert surface["all_getprocaddress_call_count"] == 100
    assert surface["all_unique_resolver_callers"] == 18
    assert surface["directly_reachable_unique_resolver_callers"] == 6
    assert surface["directly_reachable_getprocaddress_call_count"] == 11


def test_exact_reachable_resolver_set_is_pinned():
    rows = load_evidence()["resolver_surface"]["directly_reachable"]
    assert [row["caller"] for row in rows] == [
        "0x0090748b",
        "0x0090aa27",
        "0x0090aa9e",
        "0x0090abb8",
        "0x009189cd",
        "0x0091c073",
    ]
    assert [row["distance"] for row in rows] == [9, 6, 6, 7, 8, 9]
    assert [row["getprocaddress_call_count"] for row in rows] == [1, 1, 1, 2, 1, 5]


def test_reachable_context_contains_no_plain_apc_names():
    rows = load_evidence()["resolver_surface"]["directly_reachable"]
    values = {
        item["value"]
        for row in rows
        for item in row["contained_strings"]
    }
    assert "QueueUserAPC" not in values
    assert "NtQueueApcThread" not in values
    assert "NtQueueApcThreadEx" not in values
    assert "ZwQueueApcThread" not in values
    assert "RtlQueueApcWow64Thread" not in values
    assert "SetWaitableTimerEx" not in values
    assert {"EncodePointer", "DecodePointer", "MessageBoxA"}.issubset(values)


def test_direct_graph_closure_does_not_overclaim_indirect_timing():
    a = load_evidence()["adjudication"]
    assert a["direct_callgraph_resolver_surface_bounded"] is True
    assert a["direct_worker_reachable_resolver_count"] == 6
    assert a["direct_worker_reachable_plain_apc_name_evidence"] is False
    assert a["indirect_callgraph_surface_ruled_out"] is False
    assert a["hashed_or_generated_resolution_ruled_out"] is False
    assert a["manual_export_walk_ruled_out"] is False
    assert a["native_or_syscall_injection_ruled_out"] is False
    assert a["controller1_timing_exhaustive"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7
