import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "verify_p1d_slot3_x87_remaining.py"
EVIDENCE = ROOT / "evidence" / "p1d_slot3_x87_remaining_closure.json"

REMAINING = {
    "FUN_00766510",
    "FUN_0075c0d0",
    "FUN_007aa940",
    "FUN_007b8630",
    "FUN_0075ada0",
    "FUN_0075afc0",
    "FUN_007876e0",
    "FUN_007ade70",
    "FUN_007b7840",
}


def load_tool():
    spec = importlib.util.spec_from_file_location("p1d_x87_remaining", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_verifier_pins_exact_remaining_set_and_critical_anchors():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert set(module.REMAINING) == REMAINING
    assert len(module.EXPECTED) == 71
    assert module.EXPECTED[0x0076D139] == "call 0x766510"
    assert module.EXPECTED[0x00771231] == "push 0x0"
    assert module.EXPECTED[0x007592B4] == "call 0x7ade70"
    assert module.EXPECTED[0x007593EB] == "call 0x7ade70"
    assert module.EXPECTED[0x00770FB1] == "mov ecx,DWORD PTR [esi+0x339c]"
    assert module.EXPECTED[0x007B82F4] == "call 0x7b7840"


def test_evidence_closes_all_eighteen_shallow_x87_candidates():
    data = load_evidence()
    assert data["format"] == "SHIFT.P1D.P13DSlot3X87RemainingClosure/1"
    assert data["ready"] is True
    assert data["authority"]["verified_machine_anchor_count"] == 71
    assert data["frontier"] == {
        "original_candidate_count": 18,
        "resolved_by_upstream_reuse_tranche": 9,
        "resolved_here": 9,
        "remaining_count": 0,
    }
    assert {row["function"] for row in data["resolved"]} == REMAINING
    assert all(row["rejected"] for row in data["resolved"])


def test_path_and_object_identity_rejections_are_explicit():
    data = load_evidence()
    rows = {row["function"]: row for row in data["resolved"]}
    assert rows["FUN_0075c0d0"]["domain"] == "bounded shallow path infeasible"
    assert "literal 0" in rows["FUN_0075c0d0"]["proof"]
    assert rows["FUN_007ade70"]["domain"] == "caller stack-local outputs"
    assert "0x007592b4" in rows["FUN_007ade70"]["proof"]
    assert "0x007593eb" in rows["FUN_007ade70"]["proof"]
    assert rows["FUN_007b8630"]["domain"] == "BODY recovery domain"
    assert rows["FUN_007b7840"]["domain"] == "BODY lifecycle/recovery state"


def test_global_gates_remain_fail_closed():
    a = load_evidence()["adjudication"]
    assert a["slot3_shallow_x87_zero_init_depth4_subset_complete"] is True
    assert a["slot3_shallow_x87_candidate_count"] == 18
    assert a["slot3_shallow_x87_rejected_count"] == 18
    assert a["slot3_shallow_x87_selected_hdvehicle_writer_found"] is False
    assert a["slot3_sse_vector_copy_init_complete"] is False
    assert a["slot3_deeper_direct_aliases_complete"] is False
    assert a["slot3_indirect_callback_aliases_complete"] is False
    assert a["slot3_writer_provenance_proven"] is False
    assert a["p1_3d_complete"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
