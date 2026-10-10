import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "verify_p1b_hdvehicle_4330_external_caller_tranche1.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_external_caller_tranche1.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1b_4330_tranche1", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_evidence_closes_exactly_first_two_callers():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330ExternalCallerTranche1/1"
    adj = data["adjudication"]
    assert adj["external_caller_tranche1_complete"] is True
    assert adj["resolved_external_caller_count"] == 2
    assert adj["resolved_external_callsite_count"] == 6
    assert adj["remaining_external_caller_count"] == 5
    assert adj["tranche1_preexisting_4330_alias_found"] is False
    assert adj["external_receiver_provenance_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_wrapper_chain_is_root_entry_not_preexisting_4330_alias():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    row = data["fun_00491d86_wrapper_chain"]
    assert row["ecx_preserved_across_wrappers"] is True
    assert row["preexisting_hdvehicle_4330_alias_forwarded"] is False
    entries = row["direct_entries_to_fun_00768a30"]
    assert [x["site"] for x in entries] == ["0x0070275c", "0x007027be", "0x0076e544"]
    assert entries[0]["receiver"] == "literal 0x00c13700 HDVehicle root"
    assert entries[1]["receiver"] == "literal 0x00c13700 HDVehicle root"


def test_fun_00798df0_cluster_has_five_non_alias_calls():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    cluster = data["fun_00798df0_cluster"]
    assert cluster["external_callsite_count"] == 5
    assert cluster["preexisting_hdvehicle_4330_alias_forwarded"] is False
    assert [row["site"] for row in cluster["calls"]] == [
        "0x00798f5c", "0x00798f9c", "0x00798fce", "0x00798fff", "0x00799054"
    ]
    stack_param3 = [row for row in cluster["calls"] if row["target"] == "FUN_007c3b00"]
    assert len(stack_param3) == 3
    assert all(row["target_exact_4330_parameter"] == "stack param3" for row in stack_param3)
    assert all(row["actual"] == "stack local EBP-0x238c" for row in stack_param3)
    assert all(row["matches_exact_4330"] is False for row in stack_param3)


def test_tool_pins_hashes_functions_and_machine_windows():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.SQLITE_SHA256 == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert set(module.EXPECTED_FUNCS) == {"0x00491d86", "0x00768a30", "0x00798df0"}
    assert len(module.WINDOWS) == 10
    assert any(va == 0x0076E1B5 for va, _, _ in module.WINDOWS)
    assert any(va == 0x00798F92 for va, _, _ in module.WINDOWS)
