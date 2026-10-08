import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_static_4330_pointer_occurrence_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_target():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Static4330PointerOccurrenceSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["target"]["subobject_address"] == "0x00c17a30"
    assert data["target"]["little_endian_bytes"] == "30 7a c1 00"


def test_exact_four_occurrences_are_known_text_wrappers():
    occ = load_evidence()["occurrences"]
    assert occ["whole_file_count"] == 4
    assert occ["all_in_text"] is True
    assert occ["non_text_count"] == 0
    assert {s["instruction_start"] for s in occ["sites"]} == {
        "0x00702715", "0x0070274d", "0x00702776", "0x007027ac"
    }
    assert occ["rdata_pointer_cell_count"] == 0
    assert occ["data_pointer_cell_count"] == 0
    assert occ["other_section_pointer_cell_count"] == 0


def test_static_pointer_surface_closes_but_runtime_aliases_remain_open():
    adj = load_evidence()["adjudication"]
    assert adj["static_exact_4330_pointer_cell_surface_complete"] is True
    assert adj["static_exact_4330_pointer_cell_count"] == 0
    assert adj["table_or_global_load_of_preinitialized_exact_4330_possible"] is False
    assert adj["all_raw_exact_pointer_occurrences_are_known_wrappers"] is True
    assert adj["global_non_literal_hdvehicle_64e8_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
