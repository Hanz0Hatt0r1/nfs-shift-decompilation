import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1b_hdvehicle_4330_indirect_entry_coverage.py"
CALLBACKS = ROOT / "evidence" / "p1b_hdvehicle_4330_runtime_callback_coverage.json"
STATIC = ROOT / "evidence" / "p1b_hdvehicle_4330_static_pointer_materialization_coverage.json"
COMPUTED = ROOT / "evidence" / "p1b_hdvehicle_4330_computed_entry_coverage.json"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_indirect_entry_coverage.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_indirect_entry_coverage", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_builder_reproduces_committed_evidence():
    module = load_module()
    built = module.build(load_json(CALLBACKS), load_json(STATIC), load_json(COMPUTED))
    assert built == load_json(EVIDENCE)
    assert module.FORMAT == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/1"


def test_bounded_classes_have_zero_exact_carrier_hits():
    evidence = load_json(EVIDENCE)
    surface = evidence["surface"]
    assert surface["composed_coverage_class_count"] == 3
    assert surface["bounded_exact_carrier_hit_count"] == 0
    assert [row["exact_carrier_hit_count"] for row in surface["coverage"]] == [0, 0, 0]
    assert surface["coverage"][0]["bounded_callback_capable_callsite_count"] == 49
    assert surface["coverage"][0]["unique_possible_callback_entrypoint_count"] == 34
    assert surface["coverage"][1]["closed_materialization_class_count"] == 4
    assert surface["coverage"][2]["closed_computed_or_loader_entry_class_count"] == 3


def test_global_gates_remain_fail_closed():
    adjudication = load_json(EVIDENCE)["adjudication"]
    assert adjudication["bounded_indirect_entry_coverage_composed"] is True
    assert adjudication["bounded_indirect_entry_exact_4330_carrier_hit_found"] is False
    for gate in (
        "runtime_callback_registration_ruled_out",
        "remaining_callback_api_families_ruled_out",
        "generic_function_pointer_stores_copies_ruled_out",
        "runtime_generated_or_copied_function_pointers_ruled_out",
        "computed_or_encoded_code_pointers_ruled_out",
        "runtime_computed_carrier_pointers_ruled_out",
        "runtime_copied_or_encoded_carrier_pointers_ruled_out",
        "indirect_entry_into_carriers_ruled_out",
        "global_runtime_derived_4330_alias_surface_complete",
        "manager_374_join_to_hdvehicle_4330_complete",
        "last_literal_0x004b86cf_rejected",
        "p1_3_control_producer_complete",
    ):
        assert adjudication[gate] is False
    assert adjudication["external_provider_count"] == 7
