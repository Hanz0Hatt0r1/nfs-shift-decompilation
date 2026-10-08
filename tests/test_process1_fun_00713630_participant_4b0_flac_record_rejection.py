import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_flac_record_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_is_indexed_flac_record_not_participant_root():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0FlacRecordRejection/1"
    assert p["candidate"]["site"] == "0x00991650"
    assert p["candidate"]["function"] == "FUN_00991540"
    assert p["candidate"]["selected_physics_participant_writer"] is False
    g = p["record_geometry"]
    assert g["record_stride"] == "0x124"
    assert g["decompiler_expression"] == "iVar4 = param_2 * 0x124 + in_EAX[1]"
    assert g["candidate_is_root_relative_participant_store"] is False


def test_parser_chain_joins_candidate_to_codec_plus_108_state():
    p = _payload()
    chain = p["parser_chain"]
    assert "FUN_00991540" in chain["FUN_009918c0"]
    assert "FUN_009918c0" in chain["FUN_00991b00"]
    assert "FUN_00991b00" in chain["FUN_00991e60"]
    assert "[this+0x108]" in chain["codec_bridge"]
    owner = p["flac_owner"]
    assert owner["initializer"] == "FUN_00963478"
    assert owner["magic_test"] == "fLaC"
    assert owner["source_path"] == "..\\..\\src\\fmod_codec_flac.cpp"


def test_machine_and_source_spans_are_pinned():
    p = _payload()
    assert p["candidate"]["machine_span"]["sha256"] == "8756a99b19110df16af96c827a6f3615b6c734b609e016f803f0a8a3bf1c004c"
    m = p["parser_chain"]["machine_spans"]
    assert m["codec_bridge_0x00963383_sha256"] == "1df1eeed61ed9829701e87f2041c77588460d377d493a6875a81075bc37fccad"
    assert m["fun_00991e60_sha256"] == "15659c25ed483e0ad71d1fb551b1678e8267a8b3311f446c34b00e0a9cb222d1"
    assert m["fun_00991b00_sha256"] == "90fab7dbd5bd8da125830b2e8a4a0db6c1439298a19a27ab37ef4990a314e32b"
    assert p["flac_owner"]["machine_span"]["sha256"] == "a4bf7504bdff4f32309ab1c519b6d470f29b36d056cc05ba73dac149315ec5ef"
    assert p["authority"]["pc_decompiler_sha256"] == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"


def test_frontier_reduces_to_eight_without_provider_promotion():
    a = _payload()["adjudication"]
    assert a["candidate_receiver_domain_closed"] is True
    assert a["candidate_is_fmod_flac_record_state"] is True
    assert a["candidate_is_selected_physics_participant"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 8
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
