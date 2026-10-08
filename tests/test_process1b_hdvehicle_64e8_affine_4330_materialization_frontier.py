import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_affine_4330_materialization_frontier.json"

def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))

def test_contract_and_authority():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Affine4330MaterializationFrontier/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["upstream_contract"] == "SHIFT.HDVehicle64e8AbsoluteRootReferenceSurface/1"

def test_exact_root_has_three_direct_affine_materializers():
    data = load_evidence()
    mats = data["exact_root_affine_materializers"]
    assert data["adjudication"]["exact_root_affine_plus_0x4330_materializer_count"] == 3
    assert [entry["function"] for entry in mats] == ["FUN_00769520", "FUN_0076b130", "FUN_0076df50"]
    assert [entry["materialization_instruction"] for entry in mats] == ["0x00769551", "0x0076b241", "0x0076e1c1"]

def test_ctor_dtor_and_large_direct_consumers_are_negative():
    data = load_evidence(); bounded = data["bounded_consumers"]
    assert bounded["FUN_00756050"]["target_access"] is False
    assert bounded["FUN_00772200"]["target_access"] is False
    assert bounded["FUN_00771c30"]["target_access"] is False
    assert bounded["FUN_0076b280"]["direct_target_access"] is False
    assert bounded["FUN_0076b280"]["forwarders_direct_target_access"] is False
    assert bounded["FUN_007618f0"]["direct_target_access"] is False
    assert bounded["FUN_007618f0"]["consumers_direct_target_access"] is False

def test_parser_body_reads_but_does_not_write_target():
    parser = load_evidence()["bounded_consumers"]["FUN_007c3b00"]
    assert parser["direct_target_read"] is True
    assert parser["direct_target_write"] is False
    assert parser["same_receiver_helper"] == "FUN_00771c30"
    assert parser["same_receiver_helper_target_access"] is False
    assert parser["deeper_exact_receiver_parser_descendants_complete"] is False

def test_frontier_remains_fail_closed():
    data = load_evidence(); frontier = data["parser_descendant_frontier"]; adj = data["adjudication"]
    assert frontier["exact_receiver_callees_still_open"]
    assert frontier["direct_literal_plus_0x21b8_access_in_listed_callees"] is False
    assert frontier["computed_or_derived_alias_writes_complete"] is False
    assert adj["affine_4330_full_descendant_surface_complete"] is False
    assert adj["non_literal_hdvehicle_64e8_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
