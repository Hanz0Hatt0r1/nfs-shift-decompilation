import json
from pathlib import Path

EVIDENCE = Path("evidence/p1d_controller1_direct_getproc_reachability.json")
DOC = Path("docs/PROCESS_1D_CONTROLLER1_GETPROC_REACHABILITY.md")
ANALYZER = Path("tools/ghidra/analyze_p1d_controller1_getproc_reachability.py")


def load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_authoritative_surface_counts_are_pinned():
    d=load()
    assert d["format"] == "SHIFT.P1D.Controller1DirectGetProcReachability/1"
    assert d["authority"]["retail_executable_md5"] == "705af8b420e5eb1e3834ac43d5533c6b"
    assert d["authority"]["function_count"] == 41538
    assert d["authority"]["call_edge_count"] == 200598
    assert d["controller1"]["worker"] == "FUN_00662880"
    assert d["controller1"]["direct_reachable_internal_function_count"] == 497
    assert d["getprocaddress_surface"]["direct_getprocaddress_callsite_count"] == 100
    assert d["getprocaddress_surface"]["direct_getprocaddress_caller_function_count"] == 18
    assert d["getprocaddress_surface"]["reachable_caller_function_count"] == 6


def test_reachable_resolver_literal_names_are_non_apc():
    d=load()
    funcs=d["getprocaddress_surface"]["reachable_functions"]
    assert {x["function"] for x in funcs} == {"0x0090748b","0x0090aa27","0x0090aa9e","0x0090abb8","0x009189cd","0x0091c073"}
    assert all(x["local_apc_name_hits"] == [] for x in funcs)
    assert d["adjudication"]["reachable_direct_named_resolver_local_literal_apc_surface_rejected"] is True


def test_gate_stays_fail_closed_beyond_local_literals():
    a=load()["adjudication"]
    assert a["nonlocal_runtime_generated_or_hashed_names_ruled_out"] is False
    assert a["manual_export_walking_ruled_out"] is False
    assert a["native_or_syscall_apc_injection_ruled_out"] is False
    assert a["controller1_timing_exhaustive"] is False
    assert a["p1_3d_complete"] is False
    assert a["external_provider_count"] == 7
    assert "local literal" in DOC.read_text(encoding="utf-8").lower()
    assert "GetProcAddress" in ANALYZER.read_text(encoding="utf-8")
