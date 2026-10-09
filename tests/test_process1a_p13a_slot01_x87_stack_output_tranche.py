import importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "verify_p1a_slot01_x87_stack_output_tranche.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_x87_stack_output_tranche_closure.json"
RESOLVED = {"FUN_00766510", "FUN_007aa940", "FUN_0075afc0", "FUN_007876e0", "FUN_007ade70"}
REMAINING = {"FUN_0075c0d0", "FUN_007b8630", "FUN_0075ada0", "FUN_007b7840"}

def load_tool():
    spec = importlib.util.spec_from_file_location("x87_stack_output", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_verifier_pins_hdvehicle_and_stack_output_anchors():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.EXPECTED[0x0076D139] == "call 0x766510"
    assert module.EXPECTED[0x00766531] == "fst QWORD PTR [esi+0x40a0]"
    assert module.EXPECTED[0x007AAA93] == "lea edx,[ebp-0x18]"
    assert module.EXPECTED[0x0076A2EB] == "lea edx,[ebp-0x4c]"
    assert module.EXPECTED[0x00787745] == "lea ecx,[ebp-0xc]"
    assert module.EXPECTED[0x007593E5] == "lea eax,[ebp-0x2c]"
    assert set(module.RESOLVED) == RESOLVED
    assert set(module.REMAINING) == REMAINING

def test_evidence_closes_five_more_and_leaves_four():
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["format"] == "SHIFT.P1A.P13ASlot01X87StackOutputTrancheClosure/1"
    assert payload["frontier"] == {
        "candidate_count": 18,
        "resolved_before": 9,
        "resolved_in_tranche": 5,
        "resolved_total": 14,
        "remaining_count": 4,
    }
    assert {row["function"] for row in payload["resolved"]} == RESOLVED
    assert all(row["rejected"] is True for row in payload["resolved"])
    assert set(payload["remaining_candidates"]) == REMAINING

def test_global_gates_remain_fail_closed():
    a = json.loads(EVIDENCE.read_text(encoding="utf-8"))["adjudication"]
    assert a["x87_stack_output_tranche_complete"] is True
    assert a["x87_stack_output_tranche_rejected_count"] == 5
    assert a["x87_resolved_total"] == 14
    assert a["x87_remaining_count"] == 4
    assert a["x87_zero_init_semantics_complete"] is False
    assert a["sse_vector_copy_init_complete"] is False
    assert a["deeper_direct_aliases_ruled_out"] is False
    assert a["indirect_callback_aliases_ruled_out"] is False
    assert a["p13a_slot0_complete"] is False and a["p13a_slot1_complete"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
