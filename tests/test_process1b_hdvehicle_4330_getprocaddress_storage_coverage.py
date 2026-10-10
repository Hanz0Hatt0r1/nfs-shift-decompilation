import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence/p1b_hdvehicle_4330_getprocaddress_storage_coverage.json'

def test_composed_surface():
    d=json.loads(EV.read_text())
    assert d['format']=='SHIFT.P1B.HDVehicle4330GetProcAddressStorageCoverage/1'
    s=d['surface']
    assert s['physical_getprocaddress_callsite_count']==101
    assert s['direct_iat_callsite_count']==12
    assert s['iat_load_root_count']==7
    assert s['register_loaded_callsite_count']==89
    assert s['generic_wrapper_direct_caller_count']==12
    assert s['generic_wrapper_persistent_nonstack_store_count']==0
    assert s['direct_iat_persistent_global_lineage_count']==3
    assert s['direct_iat_persistent_carrier_identity_hit_count']==0
    assert s['register_loaded_family_count']==7
    assert s['register_loaded_external_module_count']==6
    assert s['register_loaded_carrier_identity_hit_count']==0
    assert s['bounded_static_getprocaddress_carrier_identity_hit_count']==0
    assert s['all_statically_reachable_imported_getprocaddress_result_lineages_covered'] is True

def test_only_bounded_gates_advance():
    a=json.loads(EV.read_text())['adjudication']
    assert a['bounded_static_getprocaddress_result_storage_complete'] is True
    assert a['bounded_static_getprocaddress_storage_can_seed_internal_carrier'] is False
    assert a['dynamic_getprocaddress_resolution_ruled_out'] is False
    assert a['runtime_generated_or_copied_function_pointers_ruled_out'] is False
    assert a['generic_function_pointer_stores_copies_ruled_out'] is False
    assert a['runtime_patching_or_generated_code_ruled_out'] is False
    assert a['runtime_computed_carrier_pointers_ruled_out'] is False
    assert a['runtime_copied_or_encoded_carrier_pointers_ruled_out'] is False
    assert a['indirect_entry_into_carriers_ruled_out'] is False
    assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
    assert a['last_literal_0x004b86cf_rejected'] is False
    assert a['p1_3_control_producer_complete'] is False
    assert a['external_provider_count']==7

def test_upstream_contracts_are_pinned():
    d=json.loads(EV.read_text())
    assert d['upstream_contracts']==[
      'SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/2',
      'SHIFT.P1B.HDVehicle4330GetProcAddressWrapperOutputPersistence/1',
      'SHIFT.P1B.HDVehicle4330GetProcAddressDirectResultLineage/1',
      'SHIFT.P1B.HDVehicle4330GetProcAddressRegisterLoadedResultLineage/1',
    ]
