import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELECTOR_PATH = ROOT / "tools/ghidra/select_s5_physics_manager_rate_writer_targets.py"
FUNCTIONS = ROOT / "functions.jsonl"


def _load_selector():
    spec = importlib.util.spec_from_file_location(
        "select_s5_physics_manager_rate_writer_targets_retail", SELECTOR_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_retail_bounded_selection_keeps_anchor_fingerprints_and_export_cost_finite():
    module = _load_selector()
    report = module.select(FUNCTIONS)

    assert report["format"] == "SHIFT.PhysicsManagerRateWriterTargetSelection/1"
    assert report["status"] == "bounded-discovery-targets-ready"
    assert 3 <= report["target_count"] < 512, report["target_count"]

    anchors = {row["address"]: row for row in report["anchors"]}
    assert set(anchors) == {"0x0070fae0", "0x0070fe90", "0x00713050"}
    assert all(row["fingerprint_verified"] is True for row in anchors.values())

    names = report["target_names"]
    assert len(names) == len(set(names)) == report["target_count"]
    scope = report["scope"]
    assert scope["address_adjacency_proves_class_membership"] is False
    assert scope["selected_function_is_cPhysicsManager_method"] is False
    assert scope["selected_function_writes_plus_0x388"] is False
    assert scope["retail_cadence_admitted"] is False
