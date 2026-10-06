import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/s5_scheduler_push_producer_frontier.json"


def test_scheduler_push_producer_frontier_freezes_exact_next_s5_edge() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert report["format"] == "SHIFT.SchedulerPushProducerFrontier/1"
    assert report["version"] == 1
    assert report["status"] == "frontier"
    assert report["ready"] is False
    assert report["blocker"] == "retail-outer-update-scheduler-cadence-admission"

    assert report["positive_inputs"] == [
        "SHIFT.PhysicsManagerSchedulerEntryOwner/1",
        "SHIFT.SchedulerAccumulatorProducerFrontier/1",
        "SHIFT.SchedulerAccumulatorValueProvenance/1",
    ]

    abi = report["frozen_abi"]
    assert abi["caller"] == "FUN_007155e9"
    assert abi["caller_address"] == "0x007155e9"
    assert abi["caller_calling_convention"] == "__fastcall"
    assert abi["caller_explicit_parameters"] == [
        {"name": "param_1", "type": "LONG *", "storage": "ECX:4"}
    ]
    assert abi["callee"] == "FUN_00715380"
    assert abi["callee_address"] == "0x00715380"
    assert abi["callee_calling_convention"] == "__thiscall"
    assert abi["callee_explicit_float_parameter_storage"] == "Stack[0x4]:4"
    assert abi["direct_call_instruction"] == "0x00715602"

    proven = report["proven_so_far"]
    assert proven["direct_call_FUN_007155e9_to_FUN_00715380"] is True
    assert proven["callee_param1_locally_feeds_unique_this_plus_0x348_store"] is True
    assert proven["FUN_00713050_reads_this_plus_0x348_as_scheduler_accumulator"] is True
    assert proven["caller_has_no_explicit_float_argument_at_function_entry"] is True

    question = report["next_exact_question"]
    assert "PUSH/stack argument" in question["question"]
    assert "SHIFT.GhidraFunctionInstructions/2" in question["required_evidence"]
    assert "BManager/Physics Manager scheduler path" in question["promotion_condition"]


def test_scheduler_push_producer_frontier_keeps_retail_cadence_fail_closed() -> None:
    report = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    limits = report["limits"]

    assert limits["pushed_value_producer_known"] is False
    assert limits["physical_units_known"] is False
    assert limits["elapsed_seconds_semantics_proven"] is False
    assert limits["one_invocation_equals_one_rendered_frame"] is False
    assert limits["retail_cadence_admitted"] is False
    assert limits["host_1_60_is_retail_evidence"] is False
    assert limits["runtime_capture_required"] is False
    assert limits["original_game_execution_required"] is False

    assert report["consumer"] == "S5 exact retail scheduler/cadence admission proof"
    assert report["next_step"].startswith(
        "analyze the exact call-argument producer inside FUN_007155e9"
    )
