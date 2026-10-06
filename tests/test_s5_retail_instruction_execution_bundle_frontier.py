import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/s5_retail_instruction_execution_bundle_frontier.json"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_bundle_frontier_is_retained_as_cross_check_after_positive_retail_proof():
    report = _load()
    assert report["format"] == "SHIFT.S5RetailInstructionExecutionBundleFrontier/1"
    assert report["status"] == "execution-infrastructure-retained-cadence-closed-by-pinned-source-pe"
    assert report["ready"] is True
    infra = report["execution_infrastructure"]
    assert infra["bundle_target_count"] == 15
    assert infra["single_export_invocation"] is True
    assert infra["retail_result_published"] is True
    assert infra["retail_result_contract"] == "SHIFT.RetailOuterUpdateCadence/1"
    assert len(report["exact_union_targets"]) == 15
    assert len(set(report["exact_union_targets"])) == 15
    assert report["remaining_execution_requirement"] is None


def test_bundle_subsets_preserve_corrected_exact_proof_surfaces():
    subsets = _load()["exact_subsets"]
    assert subsets["scheduler"]["target_count"] == 3
    assert subsets["rate_accessor"]["target_count"] == 5
    assert subsets["bmanager"]["target_count"] == 9
    assert subsets["scheduler"]["targets"] == [
        "FUN_007155e9", "FUN_00715380", "FUN_00713050"
    ]
    assert subsets["rate_accessor"]["targets"] == [
        "FUN_00713050", "FUN_0070fe90", "FUN_0041903c", "FUN_0070fe99", "FUN_0070fae0"
    ]
    assert subsets["bmanager"]["targets"] == [
        "FUN_00647d80",
        "FUN_00647ef0",
        "FUN_0065b8b0",
        "FUN_006626a0",
        "FUN_00662880",
        "FUN_00d36000",
        "FUN_006485b0",
        "FUN_00662600",
        "FUN_0070fe90",
    ]
    corrections = _load()["corrections"]
    assert corrections["FUN_00647da0_plus_0x18_assumption_retired"] is True
    assert corrections["correct_default_dispatcher"] == "FUN_00647d80"
    assert corrections["FUN_0070fe90_return_as_controller_api_stack_argument_retired"] is True


def test_positive_retail_contract_closes_previous_bundle_gates_without_false_promotions():
    report = _load()
    gates = report["gates"]
    assert gates["scheduler_push_machine_root_published"] is True
    assert gates["physics_manager_rate_accessor_alias_published"] is True
    assert gates["bmanager_slot_plus_0x18_dispatch_published"] is True
    assert gates["plus_0x388_value_units_proven"] is True
    assert gates["retail_cadence_admitted"] is True
    limits = report["limits"]
    assert limits["synthetic_tests_are_retail_evidence"] is False
    assert limits["callgraph_adjacency_substitutes_for_instruction_operand"] is False
    assert limits["host_1_60_is_retail_evidence"] is False
    assert limits["worker_poll_10ms_is_physics_cadence"] is False
    assert limits["runtime_capture_used"] is False
    assert limits["original_game_executed"] is False
