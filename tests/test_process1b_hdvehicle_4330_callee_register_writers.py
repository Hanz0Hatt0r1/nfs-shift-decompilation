import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_callee_register_writers.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_callee_register_writer", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_direct_callee_first_span_write_through_live_slot_register():
    d = module().scan_rows([
        (0x401000, "mov", "ecx,0xb83dc0"),
        (0x401005, "call", "0x500000"),
        (0x40100A, "ret", ""),
        (0x500000, "mov", "DWORD PTR [ecx],eax"),
        (0x500002, "ret", ""),
    ])
    assert d["surface"]["direct_call_boundary_count"] == 1
    assert d["surface"]["first_span_exact_slot_writer_count"] == 1
    w = d["surface"]["first_span_exact_slot_writers"][0]
    assert w["slot"] == "0x00b83dc0"
    assert w["site"] == "0x00500000"


def test_callee_copy_alias_can_write_second_slot():
    d = module().scan_rows([
        (0x402000, "mov", "edx,0xb83ec0"),
        (0x402005, "call", "0x600000"),
        (0x40200A, "ret", ""),
        (0x600000, "mov", "eax,edx"),
        (0x600002, "mov", "DWORD PTR [eax],ecx"),
        (0x600004, "ret", ""),
    ])
    assert d["surface"]["first_span_exact_slot_writer_count"] == 1
    b = d["surface"]["direct_call_boundaries"][0]
    assert b["callee_alias_copies"][0]["dst"] == "eax"
    assert b["first_span_writes"][0]["slot"] == "0x00b83ec0"


def test_callee_clobber_removes_exact_alias():
    d = module().scan_rows([
        (0x403000, "mov", "ecx,0xb83dc0"),
        (0x403005, "call", "0x700000"),
        (0x40300A, "ret", ""),
        (0x700000, "mov", "ecx,eax"),
        (0x700002, "mov", "DWORD PTR [ecx],edx"),
        (0x700004, "ret", ""),
    ])
    assert d["surface"]["first_span_exact_slot_writer_count"] == 0


def test_semantic_gates_remain_fail_closed():
    a = module().scan_rows([])["adjudication"]
    assert a["direct_callee_register_alias_first_span_scanned"] is True
    assert a["callee_created_alias_writer_provenance_complete"] is False
    assert a["interprocedural_alias_writer_provenance_complete"] is False
    assert a["runtime_or_alias_writer_provenance_complete"] is False
    assert a["memory_derived_indirect_call_target_identity_complete"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
