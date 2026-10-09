import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_p1d_slot3_shallow_mov_loop_handoff.py"
RECEIVER = ROOT / "evidence" / "p1a_p13a_slot01_receiver_loop_machine_closure.json"
ORDINARY = ROOT / "evidence" / "p1a_p13a_slot01_ordinary_mov_loop_machine_closure.json"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_shallow_mov_loop_handoff.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1d_slot3_mov_loop", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_reproduces_checked_handoff():
    module = load_tool()
    assert module.build(RECEIVER, ORDINARY) == json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_bounded_loop_surfaces_close_fail_closed():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1D.P13DSlot3ShallowMovLoopHandoff/1"
    assert data["slot3"]["target_byte_range"] == ["HDVehicle+0x28b8", "HDVehicle+0x28bf"]
    assert data["receiver_loop_surface"] == {
        "max_direct_call_depth": 4,
        "candidate_count": 8,
        "rejected_count": 8,
        "selected_slot3_writer_found": False,
    }
    assert data["ordinary_mov_loop_surface"] == {
        "max_direct_call_depth": 4,
        "candidate_count": 5,
        "rejected_count": 5,
        "selected_slot3_writer_found": False,
    }
    adj = data["adjudication"]
    assert adj["slot3_shallow_receiver_loop_depth4_subset_complete"] is True
    assert adj["slot3_shallow_ordinary_mov_loop_depth4_subset_complete"] is True
    assert adj["slot3_straight_line_unrolled_mov_surface_complete"] is False
    assert adj["slot3_sse_custom_copy_surface_complete"] is False
    assert adj["slot3_non_entry_alias_loop_surface_complete"] is False
    assert adj["slot3_deeper_direct_copy_init_paths_complete"] is False
    assert adj["slot3_indirect_dispatch_surface_complete"] is False
    assert adj["slot3_writer_provenance_proven"] is False
    assert adj["p1_3d_complete"] is False
    assert adj["external_provider_count"] == 7


def test_proven_hdvehicle_destinations_do_not_claim_slot3_identity():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["proven_hdvehicle_destination_domains"] == [
        "HDVehicle+0xea..+0xf9",
        "HDVehicle+0x3fe0",
        "HDVehicle+0x407c/+0x3660/+0x3678",
        "HDVehicle+0x35c8 ordinary-MOV cursor range",
    ]
    assert data["authority"]["p1a_contracts_consumed_not_reowned"] is True
