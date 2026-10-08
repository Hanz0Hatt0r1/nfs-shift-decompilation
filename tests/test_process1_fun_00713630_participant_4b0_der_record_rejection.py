import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_der_record_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_maps_to_nested_outer_8c0_not_root_4b0():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0DerRecordRejection/1"
    assert p["candidate"]["site"] == "0x00607f22"
    assert p["candidate"]["function"] == "FUN_006075f0"
    assert p["candidate"]["selected_physics_participant_writer"] is False
    j = p["caller_join"]
    assert j["receiver_is_nested_at_outer_offset"] == "0x410"
    assert j["candidate_storage_in_outer"] == "outer+0x8c0"
    assert j["payload_storage_in_outer"] == "outer+0x8c4"


def test_record_geometry_is_length_plus_payload_and_pinned():
    p = _payload()
    r = p["receiver_record"]
    assert r["initialization"] == "memset(param_1,0,0x5e0)"
    assert r["candidate_field"] == "param_1+0x4b0 = blob length"
    assert r["candidate_payload"] == "memcpy(param_1+0x4b4, source, length)"
    assert r["second_blob_length"] == "param_1+0x5b4"
    assert r["second_blob_payload"] == "param_1+0x5b8"
    f = p["source_fingerprints"]
    assert f["fun_006075f0_sha256"] == "6401ea922e4bbb7666b1fc09e4c1d9ae25fdc444ef3b7cfbb62eef4b4c54e684"
    assert f["fun_00608720_sha256"] == "46cb13f19c76a38862096fb923e869fa6fa1006475de51e6253557b87028e69f"
    assert f["fun_006087c0_sha256"] == "6efe7b55700bb6d66f2538939f3a158cdec532c98879849ff8b6174f2ca6c84c"


def test_frontier_reduces_to_one_without_provider_promotion():
    a = _payload()["adjudication"]
    assert a["candidate_receiver_domain_closed"] is True
    assert a["candidate_is_selected_physics_participant"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 1
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
