import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence/p1b_hdvehicle_4330_getprocaddress_register_loaded_lineage.json'

def test_surface_counts_and_modules():
    d=json.loads(EV.read_text())
    assert d['format']=='SHIFT.P1B.HDVehicle4330GetProcAddressRegisterLoadedResultLineage/1'
    s=d['surface']
    assert s['register_loaded_callsite_count']==89
    assert s['family_count']==7
    assert [x['callsite_count'] for x in s['families']]==[2,4,5,2,6,67,3]
    assert s['external_module_count']==6
    assert s['all_resolved_values_external_dll_exports'] is True
    assert s['exact_internal_p1b_carrier_identity_hit_count']==0
    assert s['openal_table_slot_count']==67
    assert s['openal_table_first_offset']=='0x0'
    assert s['openal_table_last_offset']=='0x108'

def test_scoped_gates_only():
    a=json.loads(EV.read_text())['adjudication']
    assert a['cfg_aware_register_loaded_result_lineage_subset_complete'] is True
    assert a['resolver_populated_bounded_storage_surface_complete'] is True
    assert a['resolver_populated_storage_can_hold_exact_internal_p1b_carrier'] is False
    assert a['runtime_generated_or_copied_function_pointers_ruled_out'] is False
    assert a['generic_function_pointer_stores_copies_ruled_out'] is False
    assert a['dynamic_getprocaddress_resolution_ruled_out'] is False
    assert a['runtime_patching_or_generated_code_ruled_out'] is False
    assert a['indirect_entry_into_carriers_ruled_out'] is False
    assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
    assert a['last_literal_0x004b86cf_rejected'] is False
    assert a['p1_3_control_producer_complete'] is False
    assert a['external_provider_count']==7
