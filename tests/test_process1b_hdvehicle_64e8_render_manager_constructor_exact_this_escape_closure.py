import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_constructor_exact_this_escape_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_constructor_exact_this_machine_surface():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerConstructorExactThisEscapeClosure/1"
    assert data["ready"] is True
    ctor = data["constructor"]
    assert ctor["entry"] == "0x0045ef50"
    assert ctor["exclusive_end"] == "0x0045f630"
    assert ctor["exact_this_capture"] == "0x0045ef59 mov esi,ecx"
    assert ctor["memory_stores_with_exact_this_as_value_count"] == 0
    assert ctor["helper_argument_transfers_of_exact_this_count"] == 0
    assert ctor["mov_ecx_esi_count"] == 0
    assert ctor["mov_edx_esi_count"] == 0
    assert ctor["push_esi_after_capture_count"] == 0
    assert ctor["returns_exact_this_in_eax"] is True


def test_constructor_path_closes_only_pre_global_escape():
    adj = load_evidence()["adjudication"]
    assert adj["constructor_creates_persistent_exact_root_copy"] is False
    assert adj["constructor_forwards_exact_root_to_opaque_helper"] is False
    assert adj["pre_global_store_constructor_escape_surface_closed_negative"] is True
    assert adj["external_or_unknown_origin_alias_copies_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
