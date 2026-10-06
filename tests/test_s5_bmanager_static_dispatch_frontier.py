import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "s5_bmanager_static_dispatch_frontier.json"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_bmanager_static_frontier_remains_fail_closed():
    payload = _load()
    assert payload["format"] == "SHIFT.BManagerStaticDispatchFrontier/1"
    assert payload["status"] == "frontier"
    assert payload["retail_cadence_admitted"] is False
    assert payload["gates_changed"] == []


def test_source_backed_physics_manager_slot_is_frozen():
    owner = _load()["upstream_positive"]
    assert owner["format"] == "SHIFT.PhysicsManagerSchedulerEntryOwner/1"
    assert owner["owner"] == "MWL::Core::cPhysicsManager"
    assert owner["vtable_address"] == "0x00b04524"
    assert owner["slot_offset"] == "0x18"
    assert owner["target"] == "FUN_00711b50"


def test_two_instruction_level_edges_remain_explicit_blockers():
    payload = _load()
    missing = {row["id"]: row for row in payload["exact_missing_machine_edges"]}
    assert set(missing) == {
        "lifecycle-indirect-slot-operand",
        "physics-manager-accessor-registration-transfer",
    }
    assert missing["lifecycle-indirect-slot-operand"]["callsite"] == "0x00647e23"
    assert all(row["proven"] is False for row in missing.values())


def test_static_adjacency_does_not_promote_dispatch_or_tick_semantics():
    payload = _load()
    adjudication = payload["adjudication"]
    assert adjudication["controller_helper_to_lifecycle_candidate_verified"] is True
    assert adjudication["controller_api_to_core_add_path_verified"] is True
    assert adjudication["candidate_indirect_operand_matches_cPhysicsManager_slot_plus_0x18"] is False
    assert adjudication["physics_manager_accessor_return_is_registration_argument"] is False
    assert adjudication["bmanager_controller_to_cPhysicsManager_slot_plus_0x18_proven"] is False
    assert payload["limits"]["FUN_00647da0_semantic_name_tick_promoted"] is False
    assert payload["limits"]["callgraph_adjacency_used_as_value_transfer"] is False
