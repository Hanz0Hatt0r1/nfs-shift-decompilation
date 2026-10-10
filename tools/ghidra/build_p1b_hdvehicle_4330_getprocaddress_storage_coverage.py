#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
FORMAT='SHIFT.P1B.HDVehicle4330GetProcAddressStorageCoverage/1'
EXPECTED_PROVIDER_COUNT=7

def read(path:Path,fmt:str):
    d=json.loads(path.read_text(encoding='utf-8'))
    if d.get('format')!=fmt or d.get('ready') is not True: raise ValueError(f'bad input {path}')
    return d

def build(static_v2:Path,wrapper:Path,direct:Path,loaded:Path):
    s=read(static_v2,'SHIFT.P1B.HDVehicle4330GetProcAddressStaticResolutionSurface/2')
    w=read(wrapper,'SHIFT.P1B.HDVehicle4330GetProcAddressWrapperOutputPersistence/1')
    d=read(direct,'SHIFT.P1B.HDVehicle4330GetProcAddressDirectResultLineage/1')
    l=read(loaded,'SHIFT.P1B.HDVehicle4330GetProcAddressRegisterLoadedResultLineage/1')
    ss=s['getprocaddress_surface']; ws=w['surface']; ds=d['surface']; ls=l['surface']
    assert ss['physical_getprocaddress_callsite_count']==101
    assert ss['direct_iat_call_reference_count']==12
    assert ss['iat_load_reference_count']==7
    assert ss['register_loaded_callsite_count']==89
    assert ss['generic_wrapper_direct_caller_count']==12
    assert ws['direct_wrapper_callsite_count']==12 and ws['resolved_pointer_persistent_nonstack_store_count']==0
    assert ds['classified_direct_iat_result_lineage_count']==12 and ds['persistent_global_lineage_count']==3 and ds['persistent_carrier_identity_hit_count']==0
    assert ls['register_loaded_callsite_count']==89 and ls['family_count']==7 and ls['external_module_count']==6 and ls['exact_internal_p1b_carrier_identity_hit_count']==0
    for x in (s,w,d,l):
        adj=x['adjudication']; assert adj['external_provider_count']==EXPECTED_PROVIDER_COUNT
    return {
      'format':FORMAT,'version':1,'ready':True,'owner':'Process 1B / P1.3B',
      'upstream_contracts':[s['format'],w['format'],d['format'],l['format']],
      'surface':{
        'physical_getprocaddress_callsite_count':101,'direct_iat_callsite_count':12,'iat_load_root_count':7,
        'register_loaded_callsite_count':89,'generic_wrapper_direct_caller_count':12,
        'generic_wrapper_persistent_nonstack_store_count':0,'direct_iat_persistent_global_lineage_count':3,
        'direct_iat_persistent_carrier_identity_hit_count':0,'register_loaded_family_count':7,
        'register_loaded_external_module_count':6,'register_loaded_carrier_identity_hit_count':0,
        'bounded_static_getprocaddress_carrier_identity_hit_count':0,
        'all_statically_reachable_imported_getprocaddress_result_lineages_covered':True,
      },
      'adjudication':{
        'bounded_static_getprocaddress_result_storage_complete':True,
        'bounded_static_getprocaddress_storage_can_seed_internal_carrier':False,
        'dynamic_getprocaddress_resolution_ruled_out':False,
        'runtime_generated_or_copied_function_pointers_ruled_out':False,
        'generic_function_pointer_stores_copies_ruled_out':False,
        'runtime_patching_or_generated_code_ruled_out':False,
        'runtime_computed_carrier_pointers_ruled_out':False,
        'runtime_copied_or_encoded_carrier_pointers_ruled_out':False,
        'indirect_entry_into_carriers_ruled_out':False,
        'manager_374_join_to_hdvehicle_4330_complete':False,
        'last_literal_0x004b86cf_rejected':False,
        'p1_3_control_producer_complete':False,
        'external_provider_count':EXPECTED_PROVIDER_COUNT,
      },
      'limits':[
        'This composes only statically reachable result lineages rooted at the imported GetProcAddress IAT and the direct generic wrapper callers.',
        'Runtime-created resolver aliases, indirect/runtime-generated wrapper entry, externally supplied function pointers, unrelated runtime-populated tables and opaque dynamic resolution remain open.'
      ],
      'next_step':'Bound unrelated runtime-populated function-pointer tables and runtime-created/indirect resolver aliases before promoting global store/copy or indirect-entry gates.'
    }

def main():
    p=argparse.ArgumentParser(); p.add_argument('--static-v2',type=Path,required=True); p.add_argument('--wrapper',type=Path,required=True); p.add_argument('--direct',type=Path,required=True); p.add_argument('--loaded',type=Path,required=True); p.add_argument('--output',type=Path); a=p.parse_args()
    out=build(a.static_v2,a.wrapper,a.direct,a.loaded); text=json.dumps(out,indent=2,sort_keys=True)+'\n'; a.output.write_text(text,encoding='utf-8') if a.output else print(text,end='')
if __name__=='__main__': main()
