import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "analyze_p1a_slot01_deeper_hdvehicle_root_tranche.py"
EVIDENCE = ROOT / "evidence" / "p1a_p13a_slot01_deeper_hdvehicle_root_tranche.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1a_deeper_hdvehicle", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_machine_verifier_pins_source_receiver_and_new_callees():
    m = load_tool()
    assert m.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert m.INDEX_SHA256 == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert m.SOURCE == "FUN_0076f030"
    assert m.EXPECTED_NEW_DEPTH5 == [
        "FUN_007534b0", "FUN_0076ea70", "FUN_00901310", "FUN_0075bdc0"
    ]
    assert m.EXPECTED_BYTES[0x0076F03A] == "8bf1"
    assert m.EXPECTED_BYTES[0x0076EA91] == "c686d23c000001"
    assert m.EXPECTED_BYTES[0x0076EB51] == "dd9ea83d0000"
    assert m.EXPECTED_CALL_TARGETS[0x0076F468] == 0x007534B0
    assert m.EXPECTED_CALL_TARGETS[0x0076F4A1] == 0x0076EA70
    assert m.EXPECTED_CALL_TARGETS[0x0076F523] == 0x00901310
    assert m.EXPECTED_CALL_TARGETS[0x0076F550] == 0x0075BDC0


def test_evidence_closes_exact_four_novel_depth5_callees():
    d = load_evidence()
    assert d["format"] == "SHIFT.P1A.P13ASlot01DeeperHDVehicleRootTranche/1"
    src = d["source"]
    assert src["function"] == "FUN_0076f030"
    assert src["min_direct_depth"] == 4
    assert src["receiver"] == "selected HDVehicle root"
    assert src["direct_callee_count"] == 6
    assert src["novel_depth5_callees"] == [
        "FUN_007534b0", "FUN_0076ea70", "FUN_00901310", "FUN_0075bdc0"
    ]
    assert [row["function"] for row in d["candidate_adjudication"]] == src["novel_depth5_callees"]
    assert all(row["rejected"] is True for row in d["candidate_adjudication"])


def test_deeper_global_and_slot_gates_remain_fail_closed():
    a = load_evidence()["adjudication"]
    assert a["deeper_hdvehicle_root_tranche_source_complete"] is True
    assert a["novel_depth5_candidate_count"] == 4
    assert a["novel_depth5_rejected_count"] == 4
    assert a["selected_slot0_slot1_writer_found"] is False
    assert a["all_deeper_direct_aliases_ruled_out"] is False
    assert a["indirect_callback_aliases_ruled_out"] is False
    assert a["p13a_slot0_complete"] is False
    assert a["p13a_slot1_complete"] is False
    assert a["p1_3_control_producer_complete"] is False
    assert a["external_provider_count"] == 7
