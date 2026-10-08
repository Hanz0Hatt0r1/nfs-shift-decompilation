import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_final_direct_vtable_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_final_direct_candidate_is_vtable_owned_nonparticipant_receiver():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0FinalDirectVtableRejection/1"
    assert p["candidate"]["site"] == "0x0076019f"
    assert p["candidate"]["enclosing_method"] == "0x0075cfb0"
    r = p["receiver_identity"]
    assert r["vtable"] == "PTR_FUN_00b09a68"
    assert r["vtable_first_two_entries"] == ["0x0076b100", "0x0075cfb0"]
    assert r["candidate_method_vtable_slot"] == 1
    assert r["constructor"] == "FUN_0076b060"
    assert r["container_geometry"] == "four objects at owner+0x400 with stride 0xa80"


def test_selected_participant_has_distinct_exact_vtable():
    p = _payload()
    s = p["selected_participant_identity"]
    assert s["constructor"] == "FUN_0072ed20"
    assert s["vtable"] == "PTR_FUN_00b070a0"
    assert s["allocation_size"] == "0x2b90"
    assert s["vtable_differs_from_candidate_receiver"] is True
    assert s["vtable"] != p["receiver_identity"]["vtable"]


def test_machine_and_source_provenance_is_pinned():
    p = _payload()
    assert p["candidate"]["method_entry_span"]["sha256"] == "f6ca730eaa016d57b834d888d666daaf34a01209b40c8bcd21e3aa9202a1aad8"
    assert p["candidate"]["candidate_span"]["sha256"] == "73c77e18a65354ae889ff6135d6a2e1e61a202b6d20a91564f5b0028027e2115"
    assert p["receiver_identity"]["vtable_first_two_entries_sha256"] == "a0a7ee6292a11c8c7e582fc654bda7bd4663b43b730a9e848ce8f8d6bb089dff"
    assert p["receiver_identity"]["constructor_source_sha256"] == "3b1f5007f827389e81facc320cdf0540612484327b86523a1d0667efa33859bd"
    assert p["selected_participant_identity"]["constructor_source_sha256"] == "5620a6d7faf14c66a9a9919d8df0d7541800ac905a824f13d0218c14d30fbb83"


def test_direct_surface_closes_but_p11a_remains_fail_closed():
    a = _payload()["adjudication"]
    assert a["candidate_receiver_vtable_identity_closed"] is True
    assert a["candidate_is_selected_physics_participant"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 0
    assert a["direct_displacement_surface_exhausted"] is True
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
