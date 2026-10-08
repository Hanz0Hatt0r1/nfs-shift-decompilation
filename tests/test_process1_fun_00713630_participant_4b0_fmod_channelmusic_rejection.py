import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_fmod_channelmusic_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_is_fmod_channelmusic_owner_state():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0FmodChannelMusicRejection/1"
    c = p["candidate"]
    assert c["site"] == "0x0098e583"
    assert c["function"] == "FUN_0098e558"
    assert c["selected_physics_participant_writer"] is False
    r = p["receiver_domain"]
    assert r["subobject_offset"] == "0x48c"
    assert r["subobject_constructor_call"] == "FUN_0099dec0(this+0x48c)"
    assert r["subobject_base_vtable"] == "FMOD::ChannelReal::vftable"
    assert r["subobject_final_vtable"] == "FMOD::ChannelMusic::vftable"
    assert r["owner_backpointer_store"] == "[this+0x4dc] = this"


def test_source_proof_is_pinned():
    p = _payload()
    d = p["decompiler_proof"]
    assert p["authority"]["pc_decompiler_sha256"] == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    assert d["candidate_function_lines"] == "1201281-1201302"
    assert d["candidate_function_sha256"] == "54fb51bda540bffc09e3cc689d67f0dc96f716481a4f6d80861d8fe1ec3d986a"
    assert d["channel_base_constructor"] == "FUN_0099dec0"
    assert "ChannelReal::vftable" in d["channel_base_constructor_assignment"]


def test_frontier_reduces_to_six_without_provider_promotion():
    a = _payload()["adjudication"]
    assert a["candidate_receiver_domain_closed"] is True
    assert a["candidate_is_fmod_audio_state"] is True
    assert a["candidate_is_selected_physics_participant"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 6
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
