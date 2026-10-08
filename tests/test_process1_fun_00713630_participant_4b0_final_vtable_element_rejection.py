import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "fun_00713630_participant_4b0_final_vtable_element_rejection.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_candidate_is_vtable_owned_embedded_element():
    p = _payload()
    assert p["format"] == "SHIFT.Fun00713630Participant4b0FinalVtableElementRejection/1"
    assert p["candidate"]["site"] == "0x0076019f"
    assert p["candidate"]["entry"] == "0x0075cfb0"
    assert p["candidate"]["entry_receiver_setup"] == "ESI = ECX"
    assert p["candidate"]["selected_physics_participant_writer"] is False
    v = p["vtable_join"]
    assert v["vtable_address"] == "0x00b09a68"
    assert v["slot_pair"] == ["0x0076b100", "0x0075cfb0"]
    assert v["constructor"] == "FUN_0076b060"
    assert v["constructor_installs_vtable"] is True


def test_outer_constructor_pins_four_0xa80_elements():
    p = _payload()
    e = p["embedded_element_root"]
    assert e["outer_constructor"] == "FUN_0076b130"
    assert e["vector_start"] == "outer+0x400"
    assert e["element_stride"] == "0xa80"
    assert e["element_count"] == 4
    assert e["element_constructor"] == "FUN_0076b060"
    assert e["candidate_storage"] == "element+0x4b0"
    assert e["candidate_is_outer_root_plus_0x4b0"] is False
    assert e["candidate_is_separately_allocated_0x2b90_participant_root"] is False


def test_direct_surface_exhausted_but_p1a_remains_fail_closed():
    a = _payload()["adjudication"]
    assert a["candidate_receiver_domain_closed"] is True
    assert a["direct_displacement_site_rejected"] is True
    assert a["remaining_unjoined_direct_site_count"] == 0
    assert a["direct_displacement_surface_identity_complete"] is True
    assert a["selected_participant_runtime_plus_0x4b0_writer_closed"] is False
    assert a["p1_1a_complete"] is False
    assert a["p1_1_complete"] is False
    assert a["contact_response_provider_removal_authorized"] is False
    assert a["external_provider_count"] == 7
