import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_fun00481e20_bulkcopy_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_and_all_direct_destination_families_are_closed():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0Fun00481e20BulkCopyRejection/1"
    assert p["candidate"]["site"] == "0x00482a5a"
    assert p["candidate"]["function"] == "FUN_00481e20"
    assert p["candidate"]["selected_physics_participant_writer"] is False
    rows = p["direct_destination_surface"]
    assert {r["callsite"] for r in rows} == {"0x0070db29", "0x004848f5", "0x0081d335"}
    assert rows[0]["selected_participant_root"] is False
    assert rows[1]["candidate_store_maps_to"] == "participant parent + 0xeb0"
    assert rows[1]["selected_participant_plus_0x4b0"] is False
    assert rows[2]["selected_participant_root"] is False


def test_machine_windows_are_pinned():
    p = _payload()
    assert p["candidate"]["writer_machine_span"]["sha256"] == "8fab6a1db52f430fd2203b7ebd3683e77eb6f3c37877b734d3ee3bc8e5ac0e76"
    rows = p["direct_destination_surface"]
    assert rows[0]["machine_span_sha256"] == "8e3c7a0e787e9fafb5471df9b20361d76e6135cfc98a0f29f51762988ac099be"
    assert rows[1]["machine_span_sha256"] == "b3053a69379c42b6facc7c99a6b1fc407897ee7621a06602fc3dc4531b31f05c"
    assert rows[2]["machine_span_sha256"] == "c525f0e6469f6831376d6e27d489cc15288d42c431f96868ca75876a1fa78850"


def test_frontier_reduces_to_nine_without_provider_promotion():
    a = _payload()["adjudication"]
    assert a["fun_00481e20_direct_destination_surface_closed"] is True
    assert a["candidate_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 9
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
