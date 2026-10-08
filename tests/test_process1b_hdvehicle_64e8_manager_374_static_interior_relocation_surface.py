import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_static_interior_relocation_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_range():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374StaticInteriorRelocationSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["manager"]["root"] == "0x00bc9fc0"
    assert data["manager"]["scanned_interior_range"]["size"] == "0x500"


def test_static_manager_interior_cells_are_absent():
    scan = load_evidence()["static_cell_scan"]
    assert scan["alignment_bytes"] == 4
    assert scan["sections"] == [".rdata", ".data"]
    assert scan["aligned_cells_in_manager_range"] == 0
    assert scan["can_load_static_interior_pointer_and_subtract_to_root"] is False


def test_relocation_surface_is_absent_in_shipped_pe():
    reloc = load_evidence()["relocation_surface"]
    assert reloc["coff_relocations_stripped"] is True
    assert reloc["base_relocation_directory_rva"] == "0x00000000"
    assert reloc["base_relocation_directory_size"] == "0x00000000"
    assert reloc["base_relocation_entries_available"] is False
    assert reloc["can_reconstruct_root_from_shipped_base_relocation_table"] is False


def test_frontier_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["static_interior_pointer_surface_complete"] is True
    assert adj["relocation_derived_surface_complete"] is True
    assert adj["surface_can_create_unrelated_manager_root"] is False
    assert adj["runtime_created_or_opaque_manager_root_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
