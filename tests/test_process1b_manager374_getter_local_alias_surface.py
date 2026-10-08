import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_manager_374_getter_local_alias_surface.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_authority_and_scope_counts():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8Manager374GetterLocalAliasSurface/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["scope"]["immediate_push_eax_after_getter_count"] == 0
    assert data["scope"]["immediate_local_store_count"] == 2
    assert data["scope"]["immediate_local_store_functions"] == ["FUN_0051dd30", "FUN_0051e370"]


def test_fun_0051dd30_local_alias_only_enters_manager_2d8_reader():
    first = load_evidence()["local_aliases"][0]
    assert first["function"] == "FUN_0051dd30"
    assert first["local_slot"] == "[ebp-0x4]"
    assert first["store_instruction"] == "0x0051dd44"
    assert first["other_local_alias_uses"] is False
    use = first["alias_uses"][0]
    assert use["callee_entry"] == "0x004893d0"
    assert use["callee_target"] == "FUN_004d3760"
    assert use["receiver_transition"] == "manager+0x2d8 at 0x004d3769"
    assert use["writes_manager_374"] is False
    assert first["writes_manager_374"] is False


def test_fun_0051e370_alias_is_read_only_and_not_forwarded():
    second = load_evidence()["local_aliases"][1]
    assert second["function"] == "FUN_0051e370"
    assert second["local_slot"] == "[ebp-0x8]"
    assert second["alias_load_instructions"] == ["0x0051e424", "0x0051e473"]
    assert second["first_load_reads"] == ["manager+0x2d4", "manager+0x374"]
    assert second["second_load_reads"] == ["manager+0x2c4", "manager+0x2a0[index]"]
    assert second["writes_through_local_alias"] is False
    assert second["passes_local_alias_to_callee"] is False
    assert second["writes_manager_374"] is False


def test_local_alias_class_is_closed_but_global_join_stays_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["immediate_getter_local_alias_surface_complete"] is True
    assert adj["immediate_getter_stack_argument_surface_complete"] is True
    assert adj["immediate_getter_local_alias_writer_count"] == 0
    assert adj["immediate_getter_local_alias_surface_places_hdvehicle_plus_0x4330_into_manager_374"] is False
    assert adj["non_immediate_or_object_storage_alias_surface_complete"] is False
    assert adj["unrelated_manager_root_reconstruction_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
