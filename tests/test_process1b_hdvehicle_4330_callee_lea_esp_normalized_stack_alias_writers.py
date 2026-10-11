import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_callee_lea_esp_normalized_stack_alias_writers.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_lea_esp", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_lea_esp_negative_adjustment_preserves_stack_alias_identity():
    d = module().scan_rows([
        (0x401000, "mov", "ecx,0xb83dc0"),
        (0x401005, "call", "0x500000"),
        (0x40100a, "ret", ""),
        (0x500000, "mov", "DWORD PTR [esp+0x10],ecx"),
        (0x500004, "lea", "esp,[esp-0x20]"),
        (0x500008, "mov", "eax,DWORD PTR [esp+0x30]"),
        (0x50000c, "mov", "DWORD PTR [eax],edx"),
        (0x50000e, "ret", ""),
    ])
    assert d["surface"]["lea_esp_normalization_event_count"] == 1
    assert d["surface"]["lea_esp_normalized_stack_alias_writer_count"] == 1
    assert d["surface"]["lea_esp_normalized_stack_alias_writers"][0]["slot"] == "0x00b83dc0"


def test_lea_esp_positive_adjustment_preserves_second_slot():
    d = module().scan_rows([
        (0x402000, "mov", "edx,0xb83ec0"),
        (0x402005, "call", "0x600000"),
        (0x40200a, "ret", ""),
        (0x600000, "sub", "esp,0x20"),
        (0x600004, "mov", "DWORD PTR [esp+0x18],edx"),
        (0x600008, "lea", "esp,[esp+0x10]"),
        (0x60000c, "mov", "edi,DWORD PTR [esp+0x8]"),
        (0x600010, "mov", "DWORD PTR [edi],eax"),
        (0x600012, "ret", ""),
    ])
    assert d["surface"]["lea_esp_normalized_stack_alias_writer_count"] == 1
    assert d["surface"]["lea_esp_normalized_stack_alias_writers"][0]["slot"] == "0x00b83ec0"


def test_dynamic_esp_change_stops_bound():
    d = module().scan_rows([
        (0x403000, "mov", "ecx,0xb83dc0"),
        (0x403005, "call", "0x700000"),
        (0x40300a, "ret", ""),
        (0x700000, "mov", "DWORD PTR [esp+0x10],ecx"),
        (0x700004, "add", "esp,eax"),
        (0x700006, "mov", "eax,DWORD PTR [esp+0x10]"),
        (0x70000a, "mov", "DWORD PTR [eax],edx"),
    ])
    assert d["surface"]["unsupported_esp_adjustment_count"] == 1
    assert d["surface"]["lea_esp_normalized_stack_alias_writer_count"] == 0


def test_semantic_gates_remain_fail_closed():
    a = module().scan_rows([])["adjudication"]
    assert a["callee_lea_esp_normalized_stack_alias_subset_scanned"] is True
    assert a["callee_stack_pointer_normalization_complete"] is False
    assert a["nested_callee_alias_writer_provenance_complete"] is False
    assert a["interprocedural_alias_writer_provenance_complete"] is False
    assert a["runtime_or_alias_writer_provenance_complete"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
