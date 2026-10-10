import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ghidra/build_p1a_exact_carrier_text_rva_literal_closure.py"
UPSTREAM = ROOT / "evidence/p1a_p13a_exact_carrier_whole_image_pointer_literal_closure.json"
EVIDENCE = ROOT / "evidence/p1a_p13a_exact_carrier_text_rva_literal_closure.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1a_text_rva", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_evidence():
    module = load_module()
    assert module.build(load(UPSTREAM)) == load(EVIDENCE)


def test_executable_text_rva_literal_surface_is_zero_hit():
    data = load(EVIDENCE)
    assert data["format"] == "SHIFT.P1A.P13AExactCarrierTextRvaLiteralClosure/1"
    assert data["carrier_set"]["count"] == 16
    text = data["text_surface"]
    assert text["section"] == ".text"
    assert text["section_rva"] == "0x00001000"
    assert text["raw_size"] == 6964736
    assert text["encoding"] == "little-endian 32-bit RVA byte sequence"
    assert text["exact_carrier_rva_literal_hit_count"] == 0
    assert text["hits"] == []


def test_non_text_rva_matches_remain_exactly_unresolved():
    surface = load(EVIDENCE)["non_text_unresolved_surface"]
    assert surface["semantic_gate"] is False
    assert surface["raw_match_count"] == 2
    assert [(row["function"], row["rva_value"], row["section"], row["file_offset_mod4"]) for row in surface["matches"]] == [
        ("FUN_0076d100", "0x0036d100", ".rdata", 3),
        ("FUN_0076d100", "0x0036d100", ".rdata", 3),
    ]


def test_only_text_rva_literal_subset_closes():
    adj = load(EVIDENCE)["adjudication"]
    assert adj["p13a_text_exact_carrier_rva_literal_subset_complete"] is True
    assert adj["p13a_text_exact_carrier_rva_literal_hit_found"] is False
    assert adj["p13a_text_exact_carrier_rva_literal_hit_count"] == 0
    assert adj["p13a_non_text_exact_carrier_rva_matches_remain_unresolved"] is True
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
