import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_callee_cfg_alias_writers.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_callee_cfg_alias_writer", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_conditional_branch_can_reach_exact_slot_writer():
    d = module().scan_rows([
        (0x401000, "mov", "ecx,0xb83dc0"),
        (0x401005, "call", "0x500000"),
        (0x40100A, "ret", ""),
        (0x500000, "cmp", "eax,0x0"),
        (0x500003, "jne", "0x500010"),
        (0x500005, "ret", ""),
        (0x500010, "mov", "DWORD PTR [ecx],edx"),
        (0x500012, "ret", ""),
    ])
    assert d["surface"]["cfg_exact_slot_writer_count"] == 1
    assert d["surface"]["cfg_exact_slot_writers"][0]["site"] == "0x00500010"
    assert d["surface"]["cfg_exact_slot_writers"][0]["slot"] == "0x00b83dc0"


def test_alias_copy_survives_jump_successor():
    d = module().scan_rows([
        (0x402000, "mov", "edx,0xb83ec0"),
        (0x402005, "call", "0x600000"),
        (0x40200A, "ret", ""),
        (0x600000, "mov", "eax,edx"),
        (0x600002, "jmp", "0x600010"),
        (0x600010, "mov", "DWORD PTR [eax],ecx"),
        (0x600012, "ret", ""),
    ])
    assert d["surface"]["cfg_exact_slot_writer_count"] == 1
    assert d["surface"]["cfg_exact_slot_writers"][0]["slot"] == "0x00b83ec0"


def test_objdump_symbolic_bare_hex_targets_are_parsed():
    d = module().scan_rows([
        (0x404000, "mov", "ecx,0xb83dc0"),
        (0x404005, "call", "500000 <FUN_00500000>"),
        (0x40400A, "ret", ""),
        (0x500000, "jne", "500010 <LAB_00500010>"),
        (0x500005, "ret", ""),
        (0x500010, "mov", "DWORD PTR [ecx],eax"),
        (0x500012, "ret", ""),
    ])
    assert d["surface"]["direct_call_boundary_count"] == 1
    assert d["surface"]["cfg_exact_slot_writer_count"] == 1
    assert d["surface"]["cfg_exact_slot_writers"][0]["site"] == "0x00500010"


def test_nested_call_stops_cfg_alias_path():
    d = module().scan_rows([
        (0x403000, "mov", "ecx,0xb83dc0"),
        (0x403005, "call", "0x700000"),
        (0x40300A, "ret", ""),
        (0x700000, "call", "0x710000"),
        (0x700005, "mov", "DWORD PTR [ecx],eax"),
        (0x700007, "ret", ""),
    ])
    assert d["surface"]["cfg_exact_slot_writer_count"] == 0
    assert d["surface"]["nested_call_boundary_count"] == 1


def test_semantic_gates_remain_fail_closed():
    a = module().scan_rows([])["adjudication"]
    assert a["direct_callee_register_alias_cfg_subset_scanned"] is True
    assert a["callee_cfg_alias_writer_provenance_complete"] is False
    assert a["nested_callee_alias_writer_provenance_complete"] is False
    assert a["interprocedural_alias_writer_provenance_complete"] is False
    assert a["runtime_or_alias_writer_provenance_complete"] is False
    assert a["memory_derived_indirect_call_target_identity_complete"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
