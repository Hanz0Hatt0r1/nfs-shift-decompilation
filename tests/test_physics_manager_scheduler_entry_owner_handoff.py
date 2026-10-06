import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/physics_manager_scheduler_entry_owner.json"
FRONTIER = ROOT / "tools/ghidra/build_retail_outer_update_scheduler_frontier.py"


def test_positive_scheduler_entry_owner_handoff_is_exact_and_fail_closed() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    source = FRONTIER.read_text(encoding="utf-8")

    assert report["format"] == "SHIFT.PhysicsManagerSchedulerEntryOwner/1"
    assert report["version"] == 1
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["evidence_state"] == "proven-static"

    entry = report["scheduler_entry"]
    assert entry["vtable_symbol"] == "PTR_FUN_00b04524"
    assert entry["vtable_address"] == "0x00b04524"
    assert entry["slot_offset"] == 0x18
    assert entry["slot_address"] == "0x00b0453c"
    assert entry["target"] == "FUN_00711b50"
    assert entry["target_address"] == "0x00711b50"
    assert entry["neighbor_release_slot_offset"] == 0x1C
    assert entry["neighbor_release_slot_address"] == "0x00b04540"
    assert entry["neighbor_release_target"] == "FUN_0070ffb0"
    assert entry["owner_proven"] is True

    chain = report["direct_scheduler_chain"]
    assert chain["verified"] is True
    assert chain["path"] == [
        "0x00711b50",
        "0x007119c0",
        "0x007117e0",
        "0x0070f940",
        "0x007155e0",
        "0x0048ed52",
        "0x007155e9",
        "0x00715380",
        "0x00713050",
    ]
    assert chain["four_way_0x0070f940_to_0x007155e0_multiplicity_proven"] is True

    handoff = report["handoff"]
    assert handoff["physics_manager_scheduler_entry_owner_proven"] is True
    assert handoff["exact_direct_chain_to_FUN_00713050_proven"] is True
    assert handoff["indirect_controller_dispatch_proven"] is False
    assert handoff["scheduler_entry_elapsed_or_accumulator_input_proven"] is False
    assert handoff["retail_cadence_admitted"] is False
    assert handoff["consumer"].startswith("S5 retail outer-update scheduler/cadence proof")

    limits = report["limits"]
    assert limits["slot_semantic_name_tick_assumed"] is False
    assert limits["indirect_invocation_callsite_claimed"] is False
    assert limits["manager_receiver_alias_at_invocation_claimed"] is False
    assert limits["entry_invocation_cadence_claimed"] is False
    assert limits["host_1_60_promoted"] is False
    assert limits["runtime_capture_used"] is False
    assert limits["original_game_executed"] is False

    # Keep the handoff mechanically tied to the analyzer constants that
    # validate the source-backed vptr rather than the shorter heuristic table.
    for token in (
        "MANAGER_VTABLE = 0x00B04524",
        "MANAGER_SCHEDULER_SLOT_OFFSET = 0x18",
        "MANAGER_SCHEDULER_ENTRY = 0x00711B50",
        "MANAGER_RELEASE_SLOT_OFFSET = 0x1C",
        "MANAGER_RELEASE_ENTRY = 0x0070FFB0",
        "(0x00711B50, 0x007119C0, (0x00711B76,))",
        "(0x00715380, 0x00713050, (0x00715434,))",
    ):
        assert token in source


def test_handoff_does_not_promote_s5_cadence_gate() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert report["handoff"]["retail_cadence_admitted"] is False
    assert report["handoff"]["indirect_controller_dispatch_proven"] is False
    assert report["handoff"]["scheduler_entry_elapsed_or_accumulator_input_proven"] is False
