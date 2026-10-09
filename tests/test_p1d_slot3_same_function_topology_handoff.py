import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_same_function_topology_handoff.py"
UPSTREAM = ROOT / "evidence" / "p1a_p13a_slot01_same_function_topology_machine_closure.json"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_same_function_topology_handoff.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1d_slot3_topology", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_handoff():
    module = load_tool()
    assert module.build(UPSTREAM) == json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_same_function_subset_is_closed_but_interprocedural_stays_open():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.P13DSlot3SameFunctionTopologyHandoff/1"
    assert data["surface"]["candidate_count"] == 10
    assert data["surface"]["rejected_count"] == 10
    assert data["surface"]["target_f64_writer_found"] is False
    adj = data["adjudication"]
    assert adj["slot3_same_function_wheel_topology_subset_complete"] is True
    assert adj["slot3_interprocedural_wheel_alias_surface_complete"] is False
    assert adj["slot3_overlapping_bulk_copy_surface_complete"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7
