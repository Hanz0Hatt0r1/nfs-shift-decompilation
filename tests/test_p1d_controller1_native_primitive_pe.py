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


def test_nearest_entries_do_not_claim_contiguous_body_ownership():
    module = load_module()
    functions = [
        {"start": 0x1000, "address": "0x00001000", "name": "FUN_A", "size_summary": 0x10},
        {"start": 0x1020, "address": "0x00001020", "name": "FUN_B", "size_summary": 0x10},
    ]
    row = module.nearest_entries(0x1018, functions)
    assert row["ghidra_function_entry"] is None
    assert row["previous_function_entry"]["name"] == "FUN_A"
    assert row["next_function_entry"]["name"] == "FUN_B"


def test_analyze_closes_only_exact_direct_static_subsurfaces(monkeypatch, tmp_path):
    module = load_module()
    exe = tmp_path / "SHIFT.exe"
    db = tmp_path / "shift.sqlite"
    exe.write_bytes(b"MZ")
    db.write_bytes(b"db")

    monkeypatch.setattr(module, "sha256", lambda path: module.EXPECTED_PE_SHA256 if path == exe else "dbhash")
    monkeypatch.setattr(
        module,
        "load_function_entries",
        lambda path: ("SHIFT.GhidraSQLiteIndex/1", [{"start": 0x1000, "address": "0x00001000", "name": "FUN_A", "size_summary": 16}]),
    )
    monkeypatch.setattr(
        module,
        "scan_primitives",
        lambda executable, objdump="objdump": {
            "fs_segment_instruction_count": 0,
            "exact_fs30_count": 0,
            "exact_fs30_sites": [],
            "raw_sysenter_count": 1,
            "raw_sysenter_sites": [{"address": "0x00001018", "text": "sysenter", "preceding_instructions": []}],
            "raw_int2e_count": 0,
            "raw_int2e_sites": [],
        },
    )
    monkeypatch.setattr(module, "scan_direct_flow_refs", lambda executable, targets, objdump="objdump": {0x1018: []})
    monkeypatch.setattr(module, "absolute_pointer_count", lambda executable, address: 0)

    payload = module.analyze(exe, db)
    adj = payload["adjudication"]
    assert adj["exact_fs30_plus_pe_export_offset_heuristic_ruled_out"] is True
    assert adj["direct_statically_addressed_sysenter_int2e_surface_ruled_out"] is True
    assert adj["computed_or_indirect_entry_to_native_bytes_ruled_out"] is False
    assert adj["manual_export_walking_ruled_out"] is False
    assert adj["native_or_syscall_apc_injection_ruled_out"] is False
    assert adj["controller1_timing_exhaustive"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_pinned_retail_result_records_sysenter_without_overclaiming():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1D.Controller1NativePrimitivePEClosure/1"
    assert payload["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert payload["authority"]["sqlite_size_is_not_assumed_to_be_a_contiguous_function_body"] is True
    assert payload["surface"]["ghidra_function_entry_count"] == 41538
    assert payload["surface"]["fs_access"]["raw_disassembly_count"] == 3458
    assert payload["surface"]["fs_access"]["exact_fs30_count"] == 0
    assert payload["surface"]["manual_export_walk"]["candidate_count"] == 0
    native = payload["surface"]["direct_native"]
    assert native["raw_sysenter_count"] == 1
    assert native["raw_int2e_count"] == 0
    site = native["native_sites"][0]
    assert site["address"] == "0x004209c8"
    assert site["ghidra_function_entry"] is None
    assert site["direct_static_incoming_refs"] == []
    assert site["absolute_pointer_occurrence_count"] == 0
    assert site["previous_function_entry"]["address"] == "0x00420770"
    assert site["next_function_entry"]["address"] == "0x004209d0"
    assert site["preceding_instructions"][-1] == {"address": "0x004209c7", "text": "int3"}
    adj = payload["adjudication"]
    assert adj["direct_statically_addressed_sysenter_int2e_surface_ruled_out"] is True
    assert adj["computed_or_indirect_entry_to_native_bytes_ruled_out"] is False
    assert adj["native_or_syscall_apc_injection_ruled_out"] is False
    assert adj["external_provider_count"] == 7
