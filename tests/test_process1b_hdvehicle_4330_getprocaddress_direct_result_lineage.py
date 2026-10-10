import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_getprocaddress_direct_result_lineage.json"


def test_direct_result_lineage_counts_and_persistent_globals():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330GetProcAddressDirectResultLineage/1"
    assert data["ready"] is True
    s = data["surface"]
    assert s["direct_iat_callsite_count"] == 12
    assert s["classified_direct_iat_result_lineage_count"] == 12
    assert s["persistent_global_lineage_count"] == 3
    assert s["persistent_exact_pointer_global_count"] == 2
    assert s["persistent_encoded_pointer_global_count"] == 1
    assert s["persistent_carrier_identity_hit_count"] == 0
    assert s["geteventhandler_helper_direct_caller_count"] == 2
    globals_by_addr = {row["global"]: row for row in s["persistent_globals"]}
    assert globals_by_addr["0x00c328c8"]["identity"] == "InitializeCriticalSectionAndSpinCount"
    assert globals_by_addr["0x00c593b0"]["identity"] == "WMCreateSyncReader"
    assert globals_by_addr["0x00cce308"]["identity"] == "ReadDirectoryChangesW"
    assert globals_by_addr["0x00c593b0"]["terminal_call"] == "0x0095073b"


def test_all_direct_iat_calls_are_classified_once():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    rows = data["surface"]["direct_calls"]
    assert len(rows) == 12
    assert len({row["callsite"] for row in rows}) == 12
    assert {row["classification"] for row in rows} >= {
        "transient_immediate_call",
        "transient_register_call",
        "bounded_return_helper",
        "persistent_encoded_global",
        "generic_wrapper_upstream_closed",
        "persistent_global",
    }


def test_scoped_direct_lineage_gates_do_not_promote_global_runtime_gates():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    adj = data["adjudication"]
    assert adj["direct_getprocaddress_result_lineage_subset_complete"] is True
    assert adj["direct_getprocaddress_persistent_global_lineage_complete"] is True
    assert adj["direct_getprocaddress_persistent_carrier_identity_found"] is False
    assert adj["register_loaded_getprocaddress_result_lineage_complete"] is False
    assert adj["dynamic_getprocaddress_resolution_ruled_out"] is False
    assert adj["runtime_generated_or_copied_function_pointers_ruled_out"] is False
    assert adj["generic_function_pointer_stores_copies_ruled_out"] is False
    assert adj["runtime_patching_or_generated_code_ruled_out"] is False
    assert adj["runtime_computed_carrier_pointers_ruled_out"] is False
    assert adj["runtime_copied_or_encoded_carrier_pointers_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
