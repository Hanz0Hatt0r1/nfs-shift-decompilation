import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_slot_address_escapes.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_slot_escape", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_exact_slot_address_push_escapes_to_direct_callee():
    m = module()
    rows = [
        (0x401000, "mov", "eax,0xb83dc0"),
        (0x401005, "push", "eax"),
        (0x401006, "call", "0x500000"),
    ]
    d = m.scan_rows(rows)
    assert d["surface"]["slot_address_escape_count"] == 1
    e = d["surface"]["slot_address_escapes"][0]
    assert e["call_target"] == "0x500000"
    assert e["slot_arguments"][0]["slot"] == "0x00b83dc0"


def test_computed_exact_second_slot_address_escapes():
    m = module()
    rows = [
        (0x402000, "mov", "ecx,0xb83e80"),
        (0x402005, "add", "ecx,0x40"),
        (0x402008, "push", "ecx"),
        (0x402009, "call", "0x600000"),
    ]
    d = m.scan_rows(rows)
    assert d["surface"]["slot_address_escape_count"] == 1
    assert d["surface"]["slot_address_escapes"][0]["slot_arguments"][0]["slot"] == "0x00b83ec0"


def test_control_boundary_drops_pending_slot_argument():
    m = module()
    rows = [
        (0x403000, "mov", "eax,0xb83dc0"),
        (0x403005, "push", "eax"),
        (0x403006, "jne", "0x403020"),
        (0x403008, "call", "0x700000"),
    ]
    d = m.scan_rows(rows)
    assert d["surface"]["slot_address_escape_count"] == 0


def test_semantic_gates_remain_fail_closed():
    a = module().scan_rows([])["adjudication"]
    assert a["slot_address_direct_callee_escape_subset_scanned"] is True
    assert a["interprocedural_alias_writer_provenance_complete"] is False
    assert a["runtime_or_alias_writer_provenance_complete"] is False
    assert a["memory_derived_indirect_call_target_identity_complete"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
