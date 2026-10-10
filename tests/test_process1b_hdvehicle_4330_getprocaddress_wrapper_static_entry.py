import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/p1b_hdvehicle_4330_getprocaddress_wrapper_static_entry.json"


def test_wrapper_static_entry_surface_is_exact_and_negative():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["format"] == "SHIFT.P1B.HDVehicle4330GetProcAddressWrapperStaticEntrySurface/1"
    assert data["ready"] is True
    surface = data["surface"]
    assert surface["wrapper_va"] == "0x0093dd2b"
    assert surface["wrapper_rva"] == "0x0053dd2b"
    assert surface["whole_image_absolute_va_literal_hit_count"] == 0
    assert surface["whole_image_rva_literal_hit_count"] == 0
    assert surface["direct_callsite_count"] == 12
    assert surface["direct_jumpsite_count"] == 0
    assert surface["source_symbol_occurrence_count"] == 13
    assert surface["source_definition_count"] == 1
    assert surface["source_direct_invocation_count"] == 12
    assert surface["source_non_invocation_value_use_count"] == 0


def test_only_scoped_static_gate_is_promoted():
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    adj = data["adjudication"]
    assert adj["generic_wrapper_static_entry_surface_complete"] is True
    assert adj["generic_wrapper_static_address_taken_or_literal_seed_found"] is False
    assert adj["generic_wrapper_static_indirect_entry_seed_found"] is False
    assert adj["generic_wrapper_indirect_runtime_entry_ruled_out"] is False
    assert adj["dynamic_getprocaddress_resolution_ruled_out"] is False
    assert adj["runtime_patching_or_generated_code_ruled_out"] is False
    assert adj["indirect_entry_into_carriers_ruled_out"] is False
    assert adj["manager_374_join_to_hdvehicle_4330_complete"] is False
    assert adj["last_literal_0x004b86cf_rejected"] is False
    assert adj["p1_3_control_producer_complete"] is False
    assert adj["external_provider_count"] == 7
