import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence/p1b_hdvehicle_4330_bounded_runtime_pointer_seed_coverage.json'

def test_surface():
    d=json.loads(EV.read_text())
    assert d['format']=='SHIFT.P1B.HDVehicle4330BoundedRuntimePointerSeedCoverage/1'
    s=d['surface']
    assert s['p1b_exact_carrier_count']==15
    assert s['nonresolver_bounded_seed_class_count']==7
    assert s['nonresolver_bounded_exact_carrier_hit_count']==0
    assert s['statically_reachable_getprocaddress_callsite_count']==101
    assert s['statically_reachable_getprocaddress_carrier_identity_hit_count']==0
    assert s['composed_bounded_seed_domain_count']==8
    assert s['composed_bounded_exact_carrier_hit_count']==0

def test_scoped_gates():
    a=json.loads(EV.read_text())['adjudication']
    assert a['bounded_runtime_pointer_seed_domains_composed'] is True
    assert a['bounded_runtime_pointer_seed_can_produce_exact_internal_carrier'] is False
    assert a['runtime_generated_or_copied_function_pointers_ruled_out'] is False
    assert a['generic_function_pointer_stores_copies_ruled_out'] is False
    assert a['runtime_computed_carrier_pointers_ruled_out'] is False
    assert a['runtime_copied_or_encoded_carrier_pointers_ruled_out'] is False
    assert a['memory_table_derived_carrier_pointers_ruled_out'] is False
    assert a['runtime_patching_or_generated_code_ruled_out'] is False
    assert a['indirect_entry_into_carriers_ruled_out'] is False
    assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
    assert a['last_literal_0x004b86cf_rejected'] is False
    assert a['p1_3_control_producer_complete'] is False
    assert a['external_provider_count']==7
