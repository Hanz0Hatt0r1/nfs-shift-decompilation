import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_global_slot_address_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_raw_occurrence_partition_is_complete():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerGlobalSlotAddressSurface/1"
    assert data["ready"] is True
    part = data["raw_occurrence_partition"]
    assert part["whole_image_little_endian_occurrence_count"] == 115
    assert part["direct_load_count"] == 112
    assert part["direct_store_count"] == 2
    assert part["slot_address_literal_materialization_count"] == 1
    assert part["partition_complete"] is True
    assert part["slot_address_literal_site"] == "0x004fb9af"


def test_simple_constant_reconstruction_has_no_hidden_target():
    data = load_evidence()
    scan = data["simple_constant_reconstruction_scan"]
    assert scan["mov_r32_imm32_seed_count"] == 38128
    assert scan["same_register_add_sub_lea_transition_count"] == 267
    assert scan["literal_target_production_count"] == 1
    assert scan["literal_target_production_sites"] == ["0x004fb9af"]
    assert scan["nonliteral_target_production_count"] == 0


def test_fail_closed_unknown_origin_frontier_remains():
    adj = load_evidence()["adjudication"]
    assert adj["all_raw_target_address_occurrences_classified"] is True
    assert adj["simple_nonliteral_constant_slot_address_reconstruction_found"] is False
    assert adj["canonical_slot_hidden_simple_arithmetic_access_surface_closed_negative"] is True
    assert adj["external_or_unknown_origin_alias_copies_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
