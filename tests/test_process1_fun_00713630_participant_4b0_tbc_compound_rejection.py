import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_tbc_compound_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_is_tbc_compound_record_not_participant():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0TbcCompoundRejection/1"
    c = p["candidate"]
    assert c["site"] == "0x007a2006"
    assert c["function"] == "FUN_007a1fc0"
    assert c["selected_physics_participant_writer"] is False
    r = p["compound_array_root"]
    assert r["owner_function"] == "FUN_007a32a0"
    assert r["section_marker"] == "[COMPOUND]"
    assert r["element_stride"] == "0x610"
    assert r["vector_constructor"] == "FUN_007a1fc0"
    assert r["array_pointer_field"] == "owner+0x10"


def test_tire_manager_source_and_machine_spans_are_pinned():
    p = _payload()
    r = p["compound_array_root"]
    assert r["source_path"] == ".\\Source\\Vehicle\\tire_manager.cpp"
    assert r["open_failure_text"] == "Could not open TBC file: %s\\n"
    assert p["authority"]["pc_decompiler_sha256"] == "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
    assert p["candidate"]["machine_span"]["sha256"] == "04891e7d3b5866252c414e211dd697a6dc516d3c137d790ab3b68a09fd733374"
    assert r["machine_span"]["sha256"] == "329198889a3c0400b6811438c6afa97ce56fc0ee43c744ae93c62a36b98116cf"


def test_frontier_reduces_to_seven_without_provider_promotion():
    a = _payload()["adjudication"]
    assert a["candidate_receiver_domain_closed"] is True
    assert a["candidate_is_tbc_compound_record"] is True
    assert a["candidate_is_selected_physics_participant"] is False
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 7
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
