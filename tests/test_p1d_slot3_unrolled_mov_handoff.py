import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_unrolled_mov_handoff.py"
UPSTREAM = ROOT / "evidence" / "p1a_p13a_slot01_unrolled_mov_copy_machine_closure.json"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_unrolled_mov_handoff.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1d_slot3_unrolled_handoff", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_checked_handoff():
    module = load_module()
    built = module.build(UPSTREAM)
    checked = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert built == checked


def test_slot3_unrolled_mov_candidate_set_is_exact():
    module = load_module()
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    assert upstream["inventory"]["candidate_functions"] == module.EXPECTED_FUNCTIONS
    assert len(module.EXPECTED_FUNCTIONS) == 11
    assert all(row["rejected"] for row in upstream["candidate_adjudication"])


def test_handoff_closes_only_bounded_unrolled_mov_subset():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.P13DSlot3UnrolledMovHandoff/1"
    assert data["slot3"]["absolute_target"] == "HDVehicle+0x28b8"
    surface = data["shallow_unrolled_mov_surface"]
    assert surface["candidate_count"] == 11
    assert surface["rejected_count"] == 11
    assert surface["selected_slot3_writer_found"] is False
    assert surface["genuine_hdvehicle_non_target_destination"] == "HDVehicle+0x40c8..+0x40d7"

    adj = data["adjudication"]
    assert adj["slot3_shallow_straight_line_unrolled_mov_depth4_subset_complete"] is True
    assert adj["slot3_straight_line_zero_init_surface_complete"] is False
    assert adj["slot3_sse_vector_custom_copy_surface_complete"] is False
    assert adj["slot3_non_entry_alias_loop_surface_complete"] is False
    assert adj["slot3_deeper_direct_alias_paths_complete"] is False
    assert adj["slot3_indirect_callback_alias_paths_complete"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_all_rejections_remain_non_slot3_destinations():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    rows = data["shallow_unrolled_mov_surface"]["candidate_rejections"]
    classes = {row["function"]: row["class"] for row in rows}
    assert classes["FUN_0075a8d0"] == "hdvehicle-root-explicit-high-offset-output"
    assert classes["FUN_007b0450"] == "statically-reachable-but-path-infeasible-optional-output"
    assert classes["FUN_007b0710"] == "collision-provider-surface-record"
    assert classes["_LocaleUpdate"] == "crt-locale-state"
    assert all(row["selected_slot3_writer"] is False for row in rows)
