import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_static_pointer_occurrence_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_target_bytes():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374StaticPointerOccurrenceSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["target"]["manager_root"] == "0x00bc9fc0"
    assert data["target"]["little_endian_bytes"] == "c0 9f bc 00"


def test_exact_three_whole_file_occurrences_are_all_text_immediates():
    occ = load_evidence()["occurrences"]
    assert occ["whole_file_count"] == 3
    assert occ["all_in_text"] is True
    assert occ["non_text_count"] == 0
    assert {s["instruction_start"] for s in occ["sites"]} == {"0x00489ae3", "0x00489afa", "0x00a9c5a0"}
    assert occ["rdata_pointer_cell_count"] == 0
    assert occ["data_pointer_cell_count"] == 0
    assert occ["other_section_pointer_cell_count"] == 0


def test_static_pointer_cells_close_but_runtime_derived_frontier_stays_open():
    adj = load_evidence()["adjudication"]
    assert adj["static_exact_pointer_cell_surface_complete"] is True
    assert adj["static_exact_pointer_cell_count"] == 0
    assert adj["table_or_global_load_of_preinitialized_exact_manager_root_possible"] is False
    assert adj["runtime_computed_or_relocated_root_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
