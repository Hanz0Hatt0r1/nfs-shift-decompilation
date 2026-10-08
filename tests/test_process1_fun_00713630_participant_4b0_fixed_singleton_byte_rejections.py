import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_fixed_singleton_byte_rejections.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_receiver_chain_is_fixed_singleton_not_selected_participant():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0FixedSingletonByteRejections/1"
    root = p["receiver_root"]
    assert root["getter"] == "FUN_00518de0"
    assert root["fixed_receiver"] == "0x00be1680"
    assert root["same_object_identity"] is False
    assert root["selected_physics_participant_root"] == "manager record[0] -> separately allocated 0x2b90 PhysicsParticipant"


def test_exact_two_sites_are_rejected_by_identity_not_width():
    p = _payload()
    rows = p["rejected_sites"]
    assert {(r["site"], r["function"]) for r in rows} == {
        ("0x0051f81c", "FUN_0051f800"),
        ("0x0051f8d2", "FUN_0051f850"),
    }
    assert all(r["receiver"] == "0x00be1680" for r in rows)
    assert all(r["selected_physics_participant_writer"] is False for r in rows)
    assert "Byte width alone" in p["limits"][0]


def test_machine_spans_and_forwarding_are_pinned():
    p = _payload()
    m = p["receiver_root"]["machine_spans"]
    assert m["getter_sha256"] == "a26109a4b6d9f0d733d810efe00fa5249945f59088bbe466906572c902db94d4"
    assert m["root_handoff_sha256"] == "fa3b5535f68a360e3f77bf15a9e26e910cbf1c97825c7e414661612e26770d75"
    assert m["dispatch_sha256"] == "f40c41c55caf51d90ffc677c3d99e49fcc9ab77b648ee3b0b240a7e6a93078b5"
    rows = p["rejected_sites"]
    assert rows[0]["machine_span_sha256"] == "a51dcb70a0a9e5e2d2ce0266d6460d70ee5b39943ad1a3ddac9be687b5c5ad92"
    assert rows[1]["machine_span_sha256"] == "aafe4ecd5dac3548843f5d6d8951d11b04ada83716b53fb2178ae956b857a1dc"


def test_frontier_reduces_but_provider_gate_stays_closed():
    a = _payload()["adjudication"]
    assert a["fixed_singleton_receiver_identity_closed"] is True
    assert a["site_0x0051f81c_rejected"] is True
    assert a["site_0x0051f8d2_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 11
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
