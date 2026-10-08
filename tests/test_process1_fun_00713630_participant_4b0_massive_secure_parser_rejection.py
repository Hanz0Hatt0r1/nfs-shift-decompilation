import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_massive_secure_parser_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_is_nested_massive_parser_workspace_not_participant_root():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0MassiveSecureParserRejection/1"
    assert p["candidate"]["site"] == "0x00607f22"
    assert p["candidate"]["actual_function"] == "FUN_006075f0"
    chain = p["receiver_chain"]
    assert chain["unique_direct_call_to_parser"] == "0x0060876a"
    assert chain["caller"] == "FUN_00608720"
    assert chain["mapping"] == "parser_receiver = *(state+0x128)+0x410; candidate storage = *(state+0x128)+0x8c0"
    assert chain["root_plus_0x4b0"] is False


def test_state_family_is_pinned_to_massive_adclient_and_plus_128():
    p = _payload()
    s = p["state_family"]
    assert s["constructor"] == "FUN_0060b1f9"
    assert s["constructor_identity"] == "MassiveAdClient3::XMassiveAdClient::vftable"
    assert s["constructor_owns_plus_0x128"] is True
    assert "[EDI+0x128]" in s["state_pointer_thunk"]
    assert s["global_creation_root"] == "FUN_0060beb7 -> FUN_0060b1f9 -> DAT_00be8618"


def test_machine_and_source_spans_are_frozen():
    p = _payload()
    assert p["candidate"]["candidate_machine_span"]["sha256"] == "e77a2361bc10b69ec6471c96896d1211437a915b1bab8efff5884f82ef0f599f"
    assert p["receiver_chain"]["caller_machine_span"]["sha256"] == "10be05754e7bec82a44ffbc177c968b1d64e68d4456c4403f09c93100808009d"
    assert p["state_family"]["state_pointer_thunk_sha256"] == "bc1d35937335586ae45be03316ff29473413f2b91aa4a8a41f5e493dc2679896"
    assert p["state_family"]["constructor_source_sha256"] == "de007a295a8dae181a27d94e4c17f3e7ba99f3e23d31f53b0bd4fe726e278a3e"
    assert p["authority"]["pc_decompiler_sha256"] == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"


def test_frontier_reduces_to_final_direct_site_without_provider_promotion():
    a = _payload()["adjudication"]
    assert a["candidate_receiver_provenance_closed"] is True
    assert a["candidate_is_massive_secure_parser_workspace"] is True
    assert a["candidate_is_selected_physics_participant_root_writer"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 1
    assert a["remaining_direct_sites"] == ["0x0076019f"]
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
