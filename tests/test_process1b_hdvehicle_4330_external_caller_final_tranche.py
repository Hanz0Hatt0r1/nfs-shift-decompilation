import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "verify_p1b_hdvehicle_4330_external_caller_final_tranche.py"
EVIDENCE = ROOT / "evidence" / "p1b_hdvehicle_4330_external_caller_final_tranche.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("p1b_4330_final", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_direct_external_surface_is_complete_but_global_gates_stay_closed():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330ExternalCallerFinalTranche/1"
    adj = data["adjudication"]
    assert adj["external_caller_final_tranche_complete"] is True
    assert adj["cumulative_resolved_external_caller_count"] == 7
    assert adj["cumulative_resolved_external_callsite_count"] == 11
    assert adj["remaining_external_caller_count"] == 0
    assert adj["external_direct_incoming_receiver_provenance_complete"] is True
    assert adj["external_direct_incoming_preexisting_4330_alias_found"] is False
    assert adj["exceptional_root_derived_4330_materializer_found"] is True
    assert adj["exceptional_root_derived_4330_materializer_bounded"] is True
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["global_runtime_derived_4330_alias_surface_complete"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7


def test_fun_00aa2850_is_literal_root_wrapper():
    row = json.loads(EVIDENCE.read_text(encoding="utf-8"))["fun_00aa2850"]
    assert row["site"] == "0x00aa2855 -> FUN_00769520"
    assert row["receiver"] == "literal ECX=0x00c13700 HDVehicle root"
    assert row["preexisting_hdvehicle_4330_alias"] is False


def test_a7063f_is_positive_exceptional_root_materializer_not_label_rejection():
    row = json.loads(EVIDENCE.read_text(encoding="utf-8"))["unwind_00a7063f"]
    assert row["shared_funcinfo"] == "0x00b71bbc"
    assert row["unwind_state"] == 8
    assert row["enclosing_exact_root_functions"] == ["FUN_00769520", "FUN_0076b130"]
    assert row["exceptional_root_derived_4330_materializer"] is True
    assert row["action"] == "ECX=[EBP-0x10]; ECX+=0x4330; tail FUN_00756050"
    assert "positive exceptional root-derived" in row["classification"]


def test_a72322_is_parent_stack_local():
    row = json.loads(EVIDENCE.read_text(encoding="utf-8"))["unwind_00a72322"]
    assert row["enclosing_function"] == "FUN_00798df0"
    assert row["enclosing_funcinfo"] == "0x00b73e7c"
    assert row["handler_push"] == "0x00798dfc -> 0x00a7234b"
    assert row["receiver"] == "LEA ECX,[EBP-0x238c] parent stack local"
    assert row["preexisting_hdvehicle_4330_alias"] is False


def test_tool_pins_eh_metadata_hashes_and_function_identities():
    module = load_tool()
    assert module.RETAIL_SHA256 == "eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
    assert module.SQLITE_SHA256 == "ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
    assert set(module.EXPECTED_FUNCS) == {
        "0x00aa2850", "0x00a7063f", "0x00a72322", "0x00769520", "0x0076b130", "0x00798df0"
    }
    assert len(module.WINDOWS) == 8
    assert any(va == 0x00A7064D for va, _, _ in module.WINDOWS)
    assert any(va == 0x00A7234B for va, _, _ in module.WINDOWS)
