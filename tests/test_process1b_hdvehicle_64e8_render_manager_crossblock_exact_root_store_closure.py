import json
from pathlib import Path

EVIDENCE = Path(__file__).parents[1] / "evidence" / "hdvehicle_64e8_render_manager_crossblock_exact_root_store_closure.json"


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_authority_are_pinned():
    data = load_evidence()
    assert data["format"] == "SHIFT.HDVehicle64e8RenderManagerCrossBlockExactRootStoreClosure/1"
    assert data["ready"] is True
    assert data["authority"]["retail_executable_sha256"] == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert data["scope"]["exact_outer_global"] == "0x00bc185c"
    assert data["scope"]["exact_direct_load_seed_count"] == 112


def test_exact_root_has_no_cross_block_persistent_store_escape():
    result = load_evidence()["result"]
    assert result["exact_root_memory_store_count"] == 0
    assert result["exact_root_push_count"] == 0
    assert result["unmodelled_exact_alias_transfer_count"] == 0


def test_only_three_derived_subobject_transitions_remain_separate():
    result = load_evidence()["result"]
    assert result["derived_subobject_transition_count"] == 3
    transitions = result["derived_subobject_transitions"]
    assert {(x["function"], x["instruction"], x["operation"]) for x in transitions} == {
        ("FUN_0040d6a0", "0x0040d83d", "lea esi,[eax+0x4]"),
        ("FUN_00498b80", "0x00498b93", "lea ecx,[edi+0x780]"),
        ("FUN_00499240", "0x004995bf", "lea ecx,[ebx+0x780]"),
    }


def test_existing_call_return_and_deref_surfaces_are_not_reclassified():
    result = load_evidence()["result"]
    assert result["exact_root_call_receiver_sink_count"] == 47
    assert result["exact_root_eax_return_sink_count"] == 9
    assert result["exact_root_dereference_sink_count"] == 77
    rel = load_evidence()["relationship_to_merged_surfaces"]
    assert rel["same_block_escape_contract"] == "SHIFT.HDVehicle64e8RenderManagerSameBlockEscapeSurface/1"
    assert rel["returned_root_direct_caller_contract"] == "SHIFT.HDVehicle64e8RenderManagerReturnedRootDirectCallerSurface/1"
    assert rel["returned_root_table_contract"] == "SHIFT.HDVehicle64e8RenderManagerTableReturnedRootClosure/1"


def test_frontier_remains_fail_closed():
    adj = load_evidence()["adjudication"]
    assert adj["cross_block_exact_root_memory_store_surface_complete"] is True
    assert adj["cross_block_exact_root_memory_store_surface_closed_negative"] is True
    assert adj["derived_subobject_alias_surface_complete"] is False
    assert adj["callee_created_or_external_exact_root_alias_surface_complete"] is False
    assert adj["two_unknown_origin_hdvehicle_4330_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
