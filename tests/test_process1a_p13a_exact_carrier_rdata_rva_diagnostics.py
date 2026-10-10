import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/analyze_p1a_exact_carrier_rdata_rva_diagnostics.py"
EVIDENCE = ROOT / "evidence/p1a_p13a_exact_carrier_rdata_rva_diagnostic_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_rdata_rva", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_machine_authority_and_table_geometry_are_pinned():
    module = load_module()
    data = load_evidence()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.TABLE_SHA256 == "85f4d25300d1437af965cebc94bf108d075b6dccff375290da83bc73aac2fb7e"
    assert module.TARGET_RVA == 0x0036D100
    assert module.MATCH_BYTES.hex() == "00d13600"
    assert data["format"] == "SHIFT.P1A.P13AExactCarrierRdataRvaDiagnosticClosure/1"
    assert len(data["tables"]) == 2
    for table in data["tables"]:
        assert table["table_size"] == 0x400
        assert table["element_width"] == 4
        assert table["element_count"] == 256
        assert table["table_sha256"] == module.TABLE_SHA256
        assert table["nondecreasing_u32"] is True


def test_both_raw_rva_matches_are_cross_dword_sequences():
    rows = load_evidence()["tables"]
    assert [(row["diagnostic_va"], row["diagnostic_offset_from_table_start"]) for row in rows] == [
        ("0x00ad443f", "0x177"),
        ("0x00b664a7", "0x177"),
    ]
    for row in rows:
        assert row["diagnostic_rva_bytes"] == "00d13600"
        assert row["diagnostic_unaligned_u32_value"] == "0x0036d100"
        assert row["diagnostic_offset_mod_element_width"] == 3
        assert row["previous_aligned_element_offset"] == "0x174"
        assert row["previous_aligned_element_value"] == "0x000032b7"
        assert row["next_aligned_element_offset"] == "0x178"
        assert row["next_aligned_element_value"] == "0x000036d1"
        assert row["diagnostic_is_aligned_table_element"] is False
        assert "cross-DWORD" in row["classification"]


def test_machine_consumers_pin_dword_binary_search_shape():
    module = load_module()
    assert module.TABLES[0]["start"] == 0x00AD42C8
    assert module.TABLES[0]["end"] == 0x00AD46C8
    assert module.TABLES[0]["callsite"] == 0x0059CD43
    assert module.TABLES[0]["callee"] == 0x00597DB0
    assert module.TABLES[0]["callee_windows"][0x00597DB0] == "8b5424088b4424042bd0c1fa02"
    assert module.TABLES[0]["callee_windows"][0x00597DD0].startswith("8bcad1f9393488")
    assert module.TABLES[1]["start"] == 0x00B66330
    assert module.TABLES[1]["end"] == 0x00B66730
    assert module.TABLES[1]["callsite"] == 0x00A485F2
    assert module.TABLES[1]["callee"] == 0x00A485A0
    assert module.TABLES[1]["callee_windows"][0x00A485A0].startswith("8bc12bd0c1fa02")
    assert "3b0c90" in module.TABLES[1]["callee_windows"][0x00A485B5]


def test_only_known_raw_rva_diagnostics_close():
    adj = load_evidence()["adjudication"]
    assert adj["p13a_non_text_exact_carrier_rva_diagnostic_subset_complete"] is True
    assert adj["p13a_non_text_exact_carrier_rva_diagnostic_count"] == 2
    assert adj["p13a_non_text_exact_carrier_rva_diagnostic_pointer_element_found"] is False
    assert adj["p13a_whole_image_raw_exact_carrier_rva_match_subset_complete"] is True
    assert adj["p13a_whole_image_raw_exact_carrier_rva_semantic_pointer_hit_found"] is False
    assert adj["relocated_or_rva_encoded_carrier_pointers_ruled_out"] is False
    assert adj["runtime_callback_registration_ruled_out"] is False
    assert adj["incoming_indirect_entry_ruled_out"] is False
    assert adj["runtime_generated_or_copied_carrier_pointers_ruled_out"] is False
    assert adj["runtime_generated_selected_wheel_pointer_stores_ruled_out"] is False
    assert adj["stored_or_escaped_aliases_ruled_out"] is False
    assert adj["p13a_slot0_complete"] is False
    assert adj["p13a_slot1_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
