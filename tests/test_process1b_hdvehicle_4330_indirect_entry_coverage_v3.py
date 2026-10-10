import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/ghidra/build_p1b_hdvehicle_4330_indirect_entry_coverage_v3.py"
BASE = ROOT / "evidence/p1b_hdvehicle_4330_indirect_entry_coverage_v2.json"
ENCODED = ROOT / "evidence/p1b_hdvehicle_4330_constant_encoded_synthesis.json"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_indirect_entry_coverage_v3.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_ie_v3", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_committed_evidence():
    module = load_module()
    assert module.build(BASE, ENCODED) == json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_v3_adds_only_bounded_encoded_class_and_keeps_global_gates_closed():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/3"
    assert data["surface"]["composed_coverage_class_count"] == 5
    assert data["surface"]["bounded_exact_carrier_hit_count"] == 0
    encoded = data["surface"]["coverage"][-1]
    assert encoded["class"] == "constant-only straight-line encoded carrier synthesis"
    assert encoded["constant_seed_count"] == 67_970
    assert encoded["recognized_transition_count"] == 2_168
    assert encoded["exact_carrier_hit_count"] == 0

    adj = data["adjudication"]
    assert adj["constant_only_encoded_carrier_synthesis_subset_included"] is True
    assert adj["computed_or_encoded_code_pointers_ruled_out"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["generic_function_pointer_stores_copies_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
