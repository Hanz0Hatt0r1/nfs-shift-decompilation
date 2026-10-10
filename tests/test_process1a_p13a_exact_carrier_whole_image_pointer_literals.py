import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1a_exact_carrier_whole_image_pointer_literals.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_exact_carrier_whole_image_pointer_literal_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_whole_image_carrier_ptr", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_authority_and_exact_zero_absolute_va_surface_are_pinned():
    module = load_module()
    data = load_evidence()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.RETAIL_SIZE == 8801792
    assert module.IMAGE_BASE == 0x00400000
    assert len(module.CARRIERS) == 16
    assert data["format"] == "SHIFT.P1A.P13AExactCarrierWholeImagePointerLiteralClosure/1"
    scan = data["absolute_va_literal_scan"]
    assert scan["encoding"] == "little-endian 32-bit absolute VA"
    assert scan["searched_file_byte_count"] == 8801792
    assert scan["hit_count"] == 0
    assert scan["hits"] == []


def test_synthetic_scanner_distinguishes_absolute_va_and_rva_bytes():
    module = load_module()
    function, address = module.CARRIERS[0]
    image_base = module.IMAGE_BASE
    absolute = address.to_bytes(4, "little")
    rva = (address - image_base).to_bytes(4, "little")
    blob = b"\x90" * 8 + absolute + b"\x90" * 5 + rva + b"\x90" * 8
    sections = [{"name":".test","raw_offset":0,"raw_size":len(blob),"rva":0x1000}]
    abs_hits, rva_hits = module.scan_literals(blob, image_base, sections)
    selected_abs = [row for row in abs_hits if row["function"] == function]
    selected_rva = [row for row in rva_hits if row["function"] == function]
    assert len(selected_abs) == 1
    assert selected_abs[0]["file_offset"] == "0x00000008"
    assert len(selected_rva) == 1
    assert selected_rva[0]["file_offset"] == "0x00000011"


def test_rva_collisions_remain_diagnostic_only():
    diag = load_evidence()["rva_diagnostics"]
    assert diag["semantic_gate"] is False
    assert diag["raw_match_count"] == 2
    assert diag["aligned_file_offset_match_count"] == 0
    assert [(row["function"], row["rva_value"], row["file_offset_mod4"]) for row in diag["matches"]] == [
        ("FUN_0076d100", "0x0036d100", 3),
        ("FUN_0076d100", "0x0036d100", 3),
    ]


def test_only_absolute_literal_subset_closes():
    adj = load_evidence()["adjudication"]
    assert adj["p13a_whole_image_exact_carrier_absolute_va_literal_subset_complete"] is True
    assert adj["p13a_whole_image_exact_carrier_absolute_va_literal_hit_found"] is False
    assert adj["p13a_whole_image_exact_carrier_absolute_va_literal_hit_count"] == 0
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["incoming_indirect_entry_ruled_out"] is False
    assert adj["relocated_or_rva_encoded_carrier_pointers_ruled_out"] is False
    assert adj["runtime_generated_or_copied_carrier_pointers_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
