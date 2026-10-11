import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_callee_stack_alias_writers.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_callee_stack_alias", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stack_spill_reload_recovers_exact_slot_writer():
    d = module().scan_rows([
        (0x401000, "mov", "ecx,0xb83dc0"),
        (0x401005, "call", "0x500000"),
        (0x40100a, "ret", ""),
        (0x500000, "mov", "DWORD PTR [ebp-0x8],ecx"),
        (0x500003, "mov", "eax,DWORD PTR [ebp-0x8]"),
        (0x500006, "mov", "DWORD PTR [eax],edx"),
        (0x500008, "ret", ""),
    ])
    assert d["surface"]["stack_alias_exact_slot_writer_count"] == 1
    assert d["surface"]["stack_alias_exact_slot_writers"][0]["slot"] == "0x00b83dc0"


def test_esp_stack_alias_recovers_second_slot_writer():
    d = module().scan_rows([
        (0x402000, "mov", "edx,0xb83ec0"),
        (0x402005, "call", "0x600000"),
        (0x40200a, "ret", ""),
        (0x600000, "mov", "DWORD PTR [esp+0x10],edx"),
        (0x600004, "mov", "edi,DWORD PTR [esp+0x10]"),
        (0x600008, "mov", "DWORD PTR [edi],eax"),
        (0x60000a, "ret", ""),
    ])
    assert d["surface"]["stack_alias_exact_slot_writer_count"] == 1
    assert d["surface"]["stack_alias_exact_slot_writers"][0]["slot"] == "0x00b83ec0"


def test_control_boundary_stops_stack_alias_trace():
    d = module().scan_rows([
        (0x403000, "mov", "ecx,0xb83dc0"),
        (0x403005, "call", "0x700000"),
        (0x40300a, "ret", ""),
        (0x700000, "mov", "DWORD PTR [ebp-0x4],ecx"),
        (0x700003, "jne", "0x700010"),
        (0x700005, "mov", "eax,DWORD PTR [ebp-0x4]"),
        (0x700008, "mov", "DWORD PTR [eax],edx"),
    ])
    assert d["surface"]["stack_alias_exact_slot_writer_count"] == 0


def test_semantic_gates_remain_fail_closed():
    a = module().scan_rows([])["adjudication"]
    assert a["callee_stack_alias_subset_scanned"] is True
    assert a["callee_stack_alias_writer_provenance_complete"] is False
    assert a["nested_callee_alias_writer_provenance_complete"] is False
    assert a["interprocedural_alias_writer_provenance_complete"] is False
    assert a["runtime_or_alias_writer_provenance_complete"] is False
    assert a["memory_derived_indirect_call_target_identity_complete"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
