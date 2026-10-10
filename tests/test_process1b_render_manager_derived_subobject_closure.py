import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "p1b_render_manager_derived_subobject_closure.json"


def load():
    return json.loads(EVIDENCE.read_text())


def test_contract_and_exact_three_transitions():
    data = load()
    assert data["format"] == "SHIFT.P1B.RenderManagerDerivedSubobjectClosure/1"
    assert data["ready"] is True
    assert data["adjudication"]["derived_subobject_transition_count"] == 3
    got = {(x["function"], x["instruction"], x["operation"]) for x in data["derived_transitions"]}
    assert got == {
        ("FUN_0040d6a0", "0x0040d83d", "lea esi,[eax+0x4]"),
        ("FUN_00498b80", "0x00498b93", "lea ecx,[edi+0x780]"),
        ("FUN_00499240", "0x004995bf", "lea ecx,[ebx+0x780]"),
    }


def test_derived_identities_do_not_reconstruct_outer_root():
    data = load()
    assert data["classification"]["outer_plus_4"]["secondary_vtable"] == "0x00ab55f0"
    assert data["classification"]["outer_plus_0x780"]["subobject_vtable"] == "0x00aebdbc"
    assert data["adjudication"]["derived_subobject_alias_surface_complete"] is True
    assert data["adjudication"]["derived_subobject_can_reconstruct_exact_outer_root"] is False


def test_global_gates_remain_fail_closed():
    adj = load()["adjudication"]
    assert adj["callee_created_or_external_exact_root_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
