import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "s5_physics_manager_rate_accessor_frontier.json"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_rate_accessor_frontier_is_fail_closed():
    payload = _load()
    assert payload["format"] == "SHIFT.PhysicsManagerRateAccessorFrontier/1"
    assert payload["status"] == "frontier"
    assert payload["retail_cadence_admitted"] is False
    assert payload["gates_changed"] == []


def test_rate_source_direct_chain_is_exact():
    payload = _load()
    assert payload["source_expression"]["accessor_callsite"] == "0x0071307c"
    assert payload["verified_direct_topology"] == [
        {"from": "FUN_00713050", "instruction": "0x0071307c", "to": "FUN_0070fe90"},
        {"from": "FUN_0070fe90", "instruction": "0x0070fe93", "to": "FUN_0041903c"},
        {"from": "FUN_0041903c", "instruction": "0x00419042", "to": "FUN_0070fe99"},
        {"from": "FUN_0070fe99", "instruction": "0x0070fec7", "to": "FUN_0070fae0"},
    ]


def test_constructor_join_does_not_promote_return_alias_or_frequency_semantics():
    payload = _load()
    join = payload["constructor_join"]
    assert join["source_backed_contract"] == "SHIFT.PhysicsManagerRuntime/1"
    assert join["named_object"] == "Physics Manager"
    assert join["vtable"] == "PTR_FUN_00b04524"
    adjudication = payload["adjudication"]
    assert adjudication["initializer_reaches_source_backed_physics_manager_constructor"] is True
    assert adjudication["FUN_0070fe90_return_aliases_cPhysicsManager_instance"] is False
    assert adjudication["plus_0x388_is_cPhysicsManager_field"] is False
    assert adjudication["plus_0x388_semantic_name_frequency"] is False
    assert adjudication["fixed_timestep_semantics_proven"] is False


def test_offset_adjacency_is_not_field_identity():
    limits = _load()["limits"]
    assert limits["offset_adjacency_used_as_field_identity"] is False
    assert limits["nearby_0x370_to_0x384_fields_used_to_promote_0x388"] is False
    assert limits["host_1_60_promoted"] is False
