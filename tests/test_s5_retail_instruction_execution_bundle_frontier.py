import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/s5_retail_instruction_execution_bundle_frontier.json"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_bundle_frontier_reduces_s5_to_one_retail_export():
    report = _load()
    assert report["format"] == "SHIFT.S5RetailInstructionExecutionBundleFrontier/1"
    assert report["status"] == "execution-infrastructure-ready"
    assert report["ready"] is False
    assert report["blocker"] == "retail-outer-update-scheduler-cadence-admission"
    infra = report["execution_infrastructure"]
    assert infra["bundle_target_count"] == 15
    assert infra["single_export_invocation"] is True
    assert infra["retail_result_published"] is False
    assert len(report["exact_union_targets"]) == 15
    assert len(set(report["exact_union_targets"])) == 15


def test_bundle_subsets_preserve_existing_exact_proof_surfaces():
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
    assert subsets["bmanager"]["targets"][-1] == "FUN_0070fe90"


def test_bundle_frontier_keeps_all_semantic_promotions_closed():
    report = _load()
    gates = report["gates"]
    assert gates["scheduler_push_machine_root_published"] is False
    assert gates["physics_manager_rate_accessor_alias_published"] is False
    assert gates["bmanager_slot_plus_0x18_dispatch_published"] is False
    assert gates["plus_0x388_value_units_proven"] is False
    assert gates["retail_cadence_admitted"] is False
    limits = report["limits"]
    assert limits["synthetic_tests_are_retail_evidence"] is False
    assert limits["callgraph_adjacency_substitutes_for_instruction_operand"] is False
    assert limits["host_1_60_is_retail_evidence"] is False
    assert limits["runtime_capture_used"] is False
    assert limits["original_game_executed"] is False
