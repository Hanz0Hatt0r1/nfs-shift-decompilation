import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1b_hdvehicle_4330_memory_target_writer_provenance.py"


def module():
    spec = importlib.util.spec_from_file_location("p1b_writer_probe", TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_scan_finds_direct_slot_writes_and_positive_call_shape():
    m = module()
    rows = [
        (0x401000, "mov", "DWORD PTR [0xb83dc0],eax"),
        (0x401005, "mov", "DWORD PTR [0xb83ec0],ecx"),
        (0x553240, "mov", "eax,DWORD PTR [esi]"),
        (0x553243, "mov", "edx,DWORD PTR [eax+0x4]"),
        (0x553247, "call", "edx"),
        (0x55399A, "mov", "eax,DWORD PTR [edi]"),
        (0x5539A8, "mov", "edx,DWORD PTR [eax+0x4]"),
        (0x5539AC, "call", "edx"),
    ]
    d = m.scan_rows(rows)
    assert d["format"] == "SHIFT.P1B.HDVehicle4330MemoryTargetWriterProvenanceProbe/1"
    assert d["slot_write_counts"]["0x00b83dc0"] == 1
    assert d["slot_write_counts"]["0x00b83ec0"] == 1
    assert len(d["positive_call_site_shapes"]) == 2
    assert all(x["present"] for x in d["positive_call_site_shapes"])
    assert all(len(x["nearby_object_plus_4_target_loads"]) == 1 for x in d["positive_call_site_shapes"])


def test_scan_keeps_semantic_gates_fail_closed():
    d = module().scan_rows([])
    a = d["adjudication"]
    assert a["writer_provenance_probe_complete"] is True
    assert a["exact_runtime_target_identity_complete"] is False
    assert a["indirect_entry_into_carriers_ruled_out"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7


def test_nonwrite_reference_is_not_promoted_to_writer():
    m = module()
    d = m.scan_rows([(0x402000, "mov", "eax,DWORD PTR [0xb83dc0]")])
    assert d["slot_reference_counts"]["0x00b83dc0"] == 1
    assert d["slot_write_counts"]["0x00b83dc0"] == 0
