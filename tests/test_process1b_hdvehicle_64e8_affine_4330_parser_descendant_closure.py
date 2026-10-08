import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_affine_4330_parser_descendant_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_upstream():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Affine4330ParserDescendantClosure/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["upstream_contract"] == "SHIFT.HDVehicle64e8Affine4330MaterializationFrontier/1"


def test_all_eleven_exact_receiver_descendants_are_bounded_negative():
    data = load_evidence()
    descendants = data["exact_receiver_descendants"]
    assert len(descendants) == 11
    assert {entry["function"] for entry in descendants} == {
        "FUN_007715f0", "FUN_007be420", "FUN_007c3920", "FUN_007bf0e0",
        "FUN_007bf590", "FUN_007bfbe0", "FUN_007bf790", "FUN_007bf6e0",
        "FUN_007c2110", "FUN_007bf430", "FUN_007bf310",
    }
    assert all(entry["target_reachable"] is False for entry in descendants)


def test_indexed_formula_bounds_stay_below_target():
    data = load_evidence()
    by_name = {entry["function"]: entry for entry in data["exact_receiver_descendants"]}
    assert by_name["FUN_007bf0e0"]["index_domain"] == "0..3"
    assert by_name["FUN_007bf0e0"]["maximum_receiver_offset"] == "+0xd78"
    bfbe0 = by_name["FUN_007bfbe0"]
    assert bfbe0["bounded_selector_chain"]["selector_domain"] == "0..4"
    assert bfbe0["bounded_selector_chain"]["maximum_receiver_offset"] == "+0xf28"
    c2110 = by_name["FUN_007c2110"]
    assert c2110["table_helper"]["selector_upper_bound"] == "0x34"
    assert c2110["table_helper"]["maximum_receiver_offset"] == "+0x1e28"
    assert by_name["FUN_007bf310"]["observed_selector_domain"] == [10, 11]


def test_c3920_hidden_same_receiver_chain_is_target_negative():
    data = load_evidence()
    c3920 = next(entry for entry in data["exact_receiver_descendants"] if entry["function"] == "FUN_007c3920")
    chains = c3920["descendant_chains"]
    assert chains[0]["chain"] == ["FUN_007725f0"]
    assert chains[0]["computed_root_range"] == ["+0x1bec", "+0x1e1c"]
    assert chains[0]["target_reachable"] is False
    assert chains[1]["chain"] == ["FUN_007c3280", "FUN_007c01f0", "FUN_007c0150"]
    assert chains[1]["exact_receiver_writes"] == ["+0x2180", "+0x1a98", "+0x1ae8"]
    assert chains[1]["target_reachable"] is False


def test_parser_surface_closes_but_global_frontier_stays_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["parser_exact_receiver_descendant_count"] == 11
    assert adj["parser_computed_or_derived_alias_surface_complete"] is True
    assert adj["parser_descendant_target_writer"] is False
    assert adj["affine_4330_materializer_descendant_surface_complete"] is True
    assert adj["affine_4330_path_writes_hdvehicle_64e8"] is False
    assert adj["global_non_literal_hdvehicle_64e8_writer_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
