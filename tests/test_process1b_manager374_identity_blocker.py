import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECT = ROOT / "evidence/hdvehicle_64e8_manager_374_exact_root_direct_callee_surface.json"
DSP = ROOT / "evidence/hdvehicle_64e8_manager_374_direct_write_dsp_rejection.json"
EVIDENCE = ROOT / "evidence/p1b_manager374_identity_blocker.json"
BUILDER = ROOT / "tools/ghidra/build_p1b_manager374_identity_blocker.py"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_manager374_blocker", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_evidence():
    module = load_module()
    assert module.build(load_json(DIRECT), load_json(DSP)) == load_json(EVIDENCE)


def test_current_blocker_is_pinned_fail_closed():
    e = load_json(EVIDENCE)
    s = e["surface"]
    a = e["adjudication"]
    assert s["exact_root_direct_callee_count"] == 9
    assert s["exact_root_direct_manager_374_writer_count"] == 1
    assert s["only_direct_nonzero_writer"] == "FUN_00d60660"
    assert s["direct_surface_places_hdvehicle_plus_0x4330_into_manager_374"] is False
    assert s["computed_direct_write_candidate_rejected_count"] == 1
    assert s["remaining_computed_runtime_path_count"] == 18
    assert s["remaining_returned_pointer_escape_path_count"] == 1
    assert s["remaining_callee_forwarding_path_count"] == 17
    assert a["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert a["last_literal_0x004b86cf_rejected"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
