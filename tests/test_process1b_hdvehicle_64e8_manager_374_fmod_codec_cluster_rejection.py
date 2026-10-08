import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_fmod_codec_cluster_rejection.json"


def payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_fmod_codec_cluster_identity_is_exact_and_bounded():
    data = payload()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374FmodCodecClusterRejection/1"
    assert data["ready"] is True
    assert data["target"]["sites"] == ["0x0097da09", "0x0097daf8", "0x0097dc63"]
    desc = data["callback_descriptor"]
    assert desc["descriptor_base"] == "0x00b9ca20"
    assert desc["process_callback"] == "FUN_0097dce4"
    assert desc["process_callback_slot"] == "0x00b9ca54"
    assert desc["reset_callback"] == "0x0097d855"
    assert desc["position_callback"] == "0x0097d86a"


def test_receiver_transfer_rejects_participants_manager_identity():
    data = payload()
    transform = data["receiver_transform"]
    assert transform["same_descriptor_domain"] is True
    assert any("arg1-0x1c" in row for row in transform["sibling_callbacks"])
    writer = data["writer_function"]
    assert writer["entry_capture"] == "0x0097d8d3 mov esi,ecx"
    assert writer["receiver_register"] == "ESI"
    assert writer["writes"] == [
        "0x0097da09 mov [esi+0x374],eax",
        "0x0097daf8 add [esi+0x374],eax",
        "0x0097dc63 mov [esi+0x374],eax",
    ]
    identity = data["identity_adjudication"]
    assert identity["receiver_is_participants_manager_root"] is False
    assert identity["receiver_is_participants_manager_subobject"] is False
    assert identity["listed_sites_can_write_manager_plus_0x374"] is False


def test_fail_closed_frontier_is_unchanged():
    adjudication = payload()["adjudication"]
    assert adjudication["fmod_codec_literal_374_cluster_complete"] is True
    assert adjudication["rejected_literal_site_count"] == 3
    assert adjudication["computed_address_writer_surface_complete"] is False
    assert adjudication["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adjudication["last_literal_0x004b86cf_rejected"] is False
    assert adjudication["p1_3_control_producer_complete"] is False
    assert adjudication["external_provider_count"] == 7
