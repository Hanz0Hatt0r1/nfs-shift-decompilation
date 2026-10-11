import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_register_slot_escapes.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_register_slot_escape", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ecx_slot_value_is_reported_at_call_boundary():
    d = module().scan_rows([
        (0x401000, "mov", "ecx,0xb83dc0"),
        (0x401005, "call", "0x500000"),
    ])
    assert d["surface"]["register_slot_escape_count"] == 1
    hit = d["surface"]["register_slot_escapes"][0]
    assert hit["call_site"] == "0x00401005"
    assert hit["register_slot_values"] == [{"register": "ecx", "slot": "0x00b83dc0"}]


def test_computed_edx_second_slot_is_reported():
    d = module().scan_rows([
        (0x402000, "mov", "edx,0xb83e80"),
        (0x402005, "add", "edx,0x40"),
        (0x402008, "call", "eax"),
    ])
    assert d["surface"]["register_slot_escape_count"] == 1
    assert d["surface"]["register_slot_escapes"][0]["register_slot_values"] == [
        {"register": "edx", "slot": "0x00b83ec0"}
    ]


def test_branch_boundary_clears_register_slot_state():
    d = module().scan_rows([
        (0x403000, "mov", "ecx,0xb83dc0"),
        (0x403005, "jne", "0x403010"),
        (0x403007, "call", "0x500000"),
    ])
    assert d["surface"]["register_slot_escape_count"] == 0


def test_call_does_not_claim_abi_or_semantic_completion():
    d = module().scan_rows([
        (0x404000, "mov", "eax,0xb83dc0"),
        (0x404005, "call", "0x500000"),
    ])
    a = d["adjudication"]
    assert a["register_held_slot_address_call_boundary_subset_scanned"] is True
    assert a["register_argument_abi_classified"] is False
    assert a["interprocedural_alias_writer_provenance_complete"] is False
    assert a["runtime_or_alias_writer_provenance_complete"] is False
    assert a["memory_derived_indirect_call_target_identity_complete"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
