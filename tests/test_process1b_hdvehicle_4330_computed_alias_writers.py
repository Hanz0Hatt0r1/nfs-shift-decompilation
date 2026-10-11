import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_computed_alias_writers.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_computed_alias", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_register_constant_alias_write_hits_selected_slot():
    m = module()
    rows = [
        (0x401000, "mov", "esi,0xb83df4"),
        (0x401005, "sub", "esi,0x34"),
        (0x401008, "mov", "DWORD PTR [esi],0xacdd68"),
    ]
    d = m.scan_rows(rows)
    assert d["format"] == "SHIFT.P1B.HDVehicle4330ComputedAliasWriterProbe/1"
    assert d["surface"]["computed_alias_writer_count"] == 1
    hit = d["surface"]["computed_alias_writers"][0]
    assert hit["resolved_address"] == "0x00b83dc0"
    assert hit["register_derived"] is True


def test_control_boundary_clears_alias_constant_state():
    m = module()
    rows = [
        (0x401000, "mov", "esi,0xb83df4"),
        (0x401005, "call", "0x500000"),
        (0x40100A, "sub", "esi,0x34"),
        (0x40100D, "mov", "DWORD PTR [esi],eax"),
    ]
    d = m.scan_rows(rows)
    assert d["surface"]["computed_alias_writer_count"] == 0


def test_scaled_index_alias_can_resolve_second_slot():
    m = module()
    rows = [
        (0x402000, "mov", "eax,0xb83e80"),
        (0x402005, "mov", "ecx,0x10"),
        (0x40200A, "mov", "DWORD PTR [eax+ecx*4],edx"),
    ]
    d = m.scan_rows(rows)
    assert d["surface"]["computed_alias_writer_count"] == 1
    assert d["surface"]["computed_alias_writers"][0]["resolved_address"] == "0x00b83ec0"


def test_semantic_gates_stay_fail_closed_without_retail_report():
    d = module().scan_rows([])
    a = d["adjudication"]
    assert a["computed_same_block_alias_writer_subset_scanned"] is True
    assert a["runtime_or_alias_writer_provenance_complete"] is False
    assert a["memory_derived_indirect_call_target_identity_complete"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
