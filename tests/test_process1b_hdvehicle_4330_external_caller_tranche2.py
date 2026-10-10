import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "verify_p1b_hdvehicle_4330_external_caller_tranche2.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_external_caller_tranche2.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1b_4330_tranche2", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tranche2_closes_two_more_external_callers():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330ExternalCallerTranche2/1"
    adj = data["adjudication"]
    assert adj["external_caller_tranche2_complete"] is True
    assert adj["cumulative_resolved_external_caller_count"] == 4
    assert adj["cumulative_resolved_external_callsite_count"] == 8
    assert adj["remaining_external_caller_count"] == 3
    assert adj["remaining_external_callers"] == [
        "FUN_00aa2850", "Unwind@00a7063f", "Unwind@00a72322"
    ]
    assert adj["tranche2_preexisting_4330_alias_found"] is False
    assert adj["external_receiver_provenance_complete"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_fun_0074da70_is_literal_root_entry():
    row = json.loads(EVIDENCE.read_text(encoding="utf-8"))["fun_0074da70"]
    assert row["site"] == "0x0074dadf -> FUN_0076df50"
    assert row["actual_receiver"] == "literal ECX=0x00c13700 HDVehicle root"
    assert row["preexisting_hdvehicle_4330_alias_forwarded"] is False


def test_fun_00795d60_forwards_stack_param3_not_4330():
    row = json.loads(EVIDENCE.read_text(encoding="utf-8"))["fun_00795d60"]
    assert row["site"] == "0x007973fe -> FUN_00771db0"
    assert row["only_direct_caller"] == "0x007990ed in FUN_00798df0"
    assert row["caller_param3_argument"] == "LEA EAX,[EBP-0x238c]; PUSH EAX"
    assert row["source_parameter"] == "FUN_00795d60 param3 loaded from [EBP+8]"
    assert row["actual_receiver"] == "stack local EBP-0x238c"
    assert row["preexisting_hdvehicle_4330_alias_forwarded"] is False


def test_tool_pins_retail_and_sqlite_identity():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.SQLITE_SHA256 == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert set(module.EXPECTED_FUNCS) == {"0x0074da70", "0x00795d60", "0x00798df0"}
    assert [va for va, _, _ in module.WINDOWS] == [0x0074DACB, 0x007990A5, 0x007973D8]
