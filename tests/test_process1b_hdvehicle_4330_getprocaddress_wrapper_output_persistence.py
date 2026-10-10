import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "tools/ghidra/analyze_p1b_hdvehicle_4330_getprocaddress_wrapper_output_persistence.py"
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_getprocaddress_wrapper_output_persistence.json"


def load_module():
    spec = importlib.util.spec_from_file_location("p1b_gpa_output", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_wrapper_output_surface_is_stack_local_and_nonpersistent():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330GetProcAddressWrapperOutputPersistence/1"
    assert data["ready"] is True
    surface = data["surface"]
    assert surface["generic_wrapper"] == "0x0093dd2b"
    assert surface["direct_wrapper_callsite_count"] == 12
    assert surface["stack_local_output_destination_count"] == 12
    assert surface["nonstack_output_destination_count"] == 0
    assert surface["unique_terminal_indirect_call_count"] == 11
    assert surface["resolved_pointer_value_copy_count_before_terminal_or_kill"] == 0
    assert surface["resolved_pointer_persistent_nonstack_store_count"] == 0
    assert len(surface["rows"]) == 12
    assert all(row["destination_class"] == "stack_local" for row in surface["rows"])
    assert all(not row["persistent_nonstack_store_before_terminal_or_kill"] for row in surface["rows"])
    assert all(not row["pointer_value_copy_before_terminal_or_kill"] for row in surface["rows"])


def test_alternative_resolution_sites_share_one_terminal_local_call():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    rows = {row["wrapper_callsite"]: row for row in data["surface"]["rows"]}
    a = rows["0x0093d06e"]
    b = rows["0x0093d086"]
    assert a["output_destination"] == b["output_destination"] == "[ebp-0x18]"
    assert a["terminal_pointer_use"] == b["terminal_pointer_use"] == "0x0093d09b"


def test_scoped_gate_advances_without_global_gate_drift():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    adj = data["adjudication"]
    assert adj["generic_wrapper_direct_output_persistence_subset_complete"] is True
    assert adj["generic_wrapper_direct_outputs_stack_local_only"] is True
    assert adj["generic_wrapper_direct_output_persistent_store_found"] is False
    assert adj["generic_wrapper_runtime_indirect_entry_ruled_out"] is False
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


def test_value_read_classifier_distinguishes_address_and_value_use():
    module = load_module()
    slot = "[ebp-0x14]"
    assert module.is_value_read("lea    eax,[ebp-0x14]", slot) is False
    assert module.is_value_read("mov    DWORD PTR [ebp-0x14],ebx", slot) is False
    assert module.is_value_read("and    DWORD PTR [ebp-0x14],0x0", slot) is False
    assert module.is_value_read("call   DWORD PTR [ebp-0x14]", slot) is True
    assert module.is_value_read("mov    eax,DWORD PTR [ebp-0x14]", slot) is True
