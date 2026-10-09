import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1d_controller1_native_primitive_pe.py"
EVIDENCE = ROOT / "evidence" / "p1d_controller1_native_primitive_pe_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_native_primitive_pe", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_function_interval_ownership_is_exact():
    module = load_module()
    functions = [
        {"start": 0x1000, "end": 0x1010, "address": "0x00001000", "name": "FUN_A"},
        {"start": 0x1020, "end": 0x1030, "address": "0x00001020", "name": "FUN_B"},
    ]
    starts = [row["start"] for row in functions]
    assert module.owner_for(0x1000, functions, starts)["name"] == "FUN_A"
    assert module.owner_for(0x100F, functions, starts)["name"] == "FUN_A"
    assert module.owner_for(0x1010, functions, starts) is None
    assert module.owner_for(0x1018, functions, starts) is None
    assert module.owner_for(0x1020, functions, starts)["name"] == "FUN_B"


def test_analyze_closes_only_exact_primitive_subsurface(monkeypatch, tmp_path):
    module = load_module()
    exe = tmp_path / "SHIFT.exe"
    db = tmp_path / "shift.sqlite"
    exe.write_bytes(b"MZ")
    db.write_bytes(b"db")

    monkeypatch.setattr(
        module,
        "sha256",
        lambda path: module.EXPECTED_PE_SHA256 if path == exe else "dbhash",
    )
    monkeypatch.setattr(
        module,
        "load_functions",
        lambda path: ("SHIFT.GhidraSQLiteIndex/1", [{"start": 0x1000, "end": 0x1010, "address": "0x00001000", "name": "FUN_A"}]),
    )
    monkeypatch.setattr(
        module,
        "scan",
        lambda executable, functions, objdump="objdump": {
            "function_count": 1,
            "fs_access": {"raw_disassembly_count": 0, "owned_function_count": 0, "exact_fs30_count": 0, "owned_exact_fs30_count": 0, "owned_operand_forms": {}},
            "manual_export_walk": {"candidate_function_count": 0, "candidate_functions": []},
            "direct_native": {"raw_sysenter_count": 0, "owned_sysenter_count": 0, "raw_int2e_count": 0, "owned_int2e_count": 0, "owned_candidate_function_count": 0, "owned_candidate_functions": [], "unowned_sysenter_sites": []},
        },
    )

    payload = module.analyze(exe, db)
    adj = payload["adjudication"]
    assert adj["exact_fs30_plus_pe_export_offset_heuristic_ruled_out"] is True
    assert adj["defined_function_sysenter_int2e_surface_ruled_out"] is True
    assert adj["manual_export_walking_ruled_out"] is False
    assert adj["native_or_syscall_apc_injection_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_pinned_retail_result_records_unowned_sysenter_without_promotion():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Controller1NativePrimitivePEClosure/1"
    assert payload["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert payload["surface"]["function_count"] == 41538
    assert payload["surface"]["fs_access"]["owned_function_count"] == 3395
    assert payload["surface"]["fs_access"]["exact_fs30_count"] == 0
    assert payload["surface"]["manual_export_walk"]["candidate_function_count"] == 0
    native = payload["surface"]["direct_native"]
    assert native["raw_sysenter_count"] == 1
    assert native["owned_sysenter_count"] == 0
    assert native["raw_int2e_count"] == 0
    assert native["unowned_sysenter_sites"][0]["address"] == "0x004209c8"
    assert native["unowned_sysenter_sites"][0]["previous_function"]["end"] == "0x0042089e"
    assert native["unowned_sysenter_sites"][0]["next_function"]["address"] == "0x004209d0"
    adj = payload["adjudication"]
    assert adj["defined_function_sysenter_int2e_surface_ruled_out"] is True
    assert adj["unowned_raw_sysenter_surface_ruled_out"] is False
    assert adj["native_or_syscall_apc_injection_ruled_out"] is False
    assert adj["external_provider_count"] == 7
