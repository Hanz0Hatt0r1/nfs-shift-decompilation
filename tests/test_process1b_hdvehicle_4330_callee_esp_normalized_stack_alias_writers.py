import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_callee_esp_normalized_stack_alias_writers.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_esp_norm", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sub_esp_spill_reload_recovers_same_logical_slot():
    d = module().scan_rows([
        (0x401000, "mov", "ecx,0xb83dc0"),
        (0x401005, "call", "0x500000"),
        (0x40100a, "ret", ""),
        (0x500000, "sub", "esp,0x20"),
        (0x500003, "mov", "DWORD PTR [esp+0x10],ecx"),
        (0x500007, "add", "esp,0x8"),
        (0x50000a, "mov", "eax,DWORD PTR [esp+0x18]"),
        (0x50000e, "mov", "DWORD PTR [eax],edx"),
        (0x500010, "ret", ""),
    ])
    assert d["surface"]["esp_normalization_event_count"] == 2
    assert d["surface"]["esp_normalized_stack_alias_writer_count"] == 1
    assert d["surface"]["esp_normalized_stack_alias_writers"][0]["slot"] == "0x00b83dc0"


def test_second_slot_survives_balanced_esp_adjustment():
    d = module().scan_rows([
        (0x402000, "mov", "edx,0xb83ec0"),
        (0x402005, "call", "0x600000"),
        (0x40200a, "ret", ""),
        (0x600000, "sub", "esp,0x10"),
        (0x600003, "mov", "DWORD PTR [esp+0x4],edx"),
        (0x600007, "add", "esp,0x10"),
        (0x60000a, "sub", "esp,0x10"),
        (0x60000d, "mov", "edi,DWORD PTR [esp+0x4]"),
        (0x600011, "mov", "DWORD PTR [edi],eax"),
        (0x600013, "ret", ""),
    ])
    assert d["surface"]["esp_normalized_stack_alias_writer_count"] == 1
    assert d["surface"]["esp_normalized_stack_alias_writers"][0]["slot"] == "0x00b83ec0"


def test_dynamic_esp_adjustment_stops_trace_without_promotion():
    d = module().scan_rows([
        (0x403000, "mov", "ecx,0xb83dc0"),
        (0x403005, "call", "0x700000"),
        (0x40300a, "ret", ""),
        (0x700000, "sub", "esp,eax"),
        (0x700002, "mov", "DWORD PTR [esp+0x4],ecx"),
        (0x700006, "ret", ""),
    ])
    assert d["surface"]["esp_normalized_stack_alias_writer_count"] == 0


def test_semantic_gates_remain_fail_closed():
    a = module().scan_rows([])["adjudication"]
    assert a["callee_esp_normalized_stack_alias_subset_scanned"] is True
    assert a["callee_stack_pointer_normalization_complete"] is False
    assert a["nested_callee_alias_writer_provenance_complete"] is False
    assert a["interprocedural_alias_writer_provenance_complete"] is False
    assert a["runtime_or_alias_writer_provenance_complete"] is False
    assert a["memory_derived_indirect_call_target_identity_complete"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
