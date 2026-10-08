import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "hdvehicle_64e8_manager_374_participants_subobject_frontier.json"
COORD = ROOT / "coordination" / "decomp_blockers.json"


def _payload():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_contract_and_manager_subobject_owner():
    p = _payload()
    assert p["format"] == "SHIFT.HDVehicle64e8Manager374ParticipantsSubobjectFrontier/1"
    assert p["ready"] is True
    assert p["manager"]["singleton_address"] == "0x00bc9fc0"
    assert p["participants_subobject"]["root_offset"] == "+0x20"
    assert p["participants_subobject"]["label"] == "Participants Manager"
    assert p["participants_subobject"]["target_relative_offset_for_manager_374"] == "+0x354"


def test_exact_adjusted_receiver_setup_calls_are_pinned():
    rows = _payload()["adjusted_receiver_setup"]["calls"]
    assert rows == [
        {
            "getter_callsite": "0x0040e83a",
            "helper_callsite": "0x0040e846",
            "helper": "FUN_00648890",
            "receiver": "FUN_00489ad0()+0x20",
        },
        {
            "getter_callsite": "0x0040e84b",
            "helper_callsite": "0x0040e855",
            "helper": "FUN_00647800",
            "receiver": "FUN_00489ad0()+0x20",
        },
    ]


def test_direct_helper_writes_do_not_reach_manager_374():
    d = _payload()["direct_helper_writes"]
    assert d["target_relative_offset"] == "+0x354"
    assert d["FUN_00648890"]["manager_root_writes"] == ["+0x17c", "+0x54", "+0x55", "+0x178"]
    assert d["FUN_00648730"]["manager_root_write"] == "+0x50"
    assert d["FUN_00647800"]["manager_root_write"] == "+0x55"
    assert d["any_direct_write_reaches_manager_374"] is False


def test_original_escape_contract_remains_bounded_and_fail_closed():
    p = _payload()
    e = p["escaped_alias_registration"]
    assert e["proven"] is True
    assert len(e["paths"]) == 2
    assert e["later_mutator_provenance_complete"] is False
    a = p["adjudication"]
    assert a["known_manager_plus_0x20_direct_helper_write_surface_reaches_manager_374"] is False
    assert a["manager_plus_0x20_escape_is_proven"] is True
    assert a["escaped_alias_consumers_closed"] is False
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["external_provider_count"] == 7


def test_coordination_preserves_escape_while_advancing_direct_lifecycle_surface():
    graph = json.loads(COORD.read_text(encoding="utf-8"))
    p13 = next(row for row in graph["workstreams"] if row["id"] == "P1.3")
    node = next(row for row in p13["children"] if row["id"] == "P1.3.manager374")
    assert node["status"] == "participants-lifecycle-zero-writers-proven-other-indirect-open"
    assert node["manager_plus_0x20_direct_helper_surface_complete"] is True
    assert node["manager_plus_0x20_escaped_alias_open"] is True
    assert node["manager_plus_0x20_lifecycle_target_reaches_0x374"] is True
    assert node["manager_plus_0x20_lifecycle_target_writes_zero_only"] is True
    assert node["participants_lifecycle_direct_target_surface_complete"] is True
    assert node["participants_lifecycle_nested_callee_surface_complete"] is False
