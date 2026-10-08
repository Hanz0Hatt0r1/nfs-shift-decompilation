import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_forwarded_receiver_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_two_forwarded_receiver_paths_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerForwardedReceiverClosure/1"
    assert data["ready"] is True
    assert data["upstream"]["bounded_direct_target_count"] == 17
    paths = data["closed_paths"]
    assert [item["direct_target"] for item in paths] == ["0x00458760", "0x0045f980"]


def test_458760_entry_root_is_never_consumed():
    path = load_evidence()["closed_paths"][0]
    assert path["exact_root_entry_register"] == "ECX"
    assert path["entry_root_consumed"] is False
    assert path["exact_outer_root_forwarded_or_persisted"] is False
    assert path["thunk_mnemonic_sha256"] == "709cfc4801a695c225264f389a8b448b0adf1c00296b77d3f5dc138c7f9658cf"
    assert path["body_mnemonic_sha256"] == "11fb3876bc0534f89a01e24b1c4c5e8e324ca1c278328a9bf18ff6fe90120b70"


def test_45f980_leaf_uses_only_derived_field_value():
    path = load_evidence()["closed_paths"][1]
    assert path["root_preservation"].startswith("0x004785f4")
    assert path["root_reforward"].startswith("0x00478608")
    assert path["leaf_thunk"] == "0x0045bfc0 -> 0x00d51560"
    assert path["leaf_root_capture"].startswith("0x00d51561")
    assert path["leaf_exact_root_store_found"] is False
    assert path["leaf_exact_root_return_found"] is False
    assert path["leaf_exact_root_reforward_found"] is False
    assert path["exact_outer_root_forwarded_beyond_leaf_or_persisted"] is False
    assert path["leaf_body_mnemonic_sha256"] == "cedb45f59e143b6b106ff80e8fd6995c06449019025ae825c4cad948f3e1377a"


def test_broader_frontier_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["closed_path_count"] == 2
    assert adj["these_forwarded_receiver_paths_closed_negative"] is True
    assert adj["opaque_callee_created_or_returned_alias_surface_complete"] is False
    assert adj["external_or_unknown_origin_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
