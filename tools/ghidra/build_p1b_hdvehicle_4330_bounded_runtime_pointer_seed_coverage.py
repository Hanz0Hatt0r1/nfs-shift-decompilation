#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
FORMAT='SHIFT.P1B.HDVehicle4330BoundedRuntimePointerSeedCoverage/1'

def load(path:Path,fmt:str):
 d=json.loads(path.read_text(encoding='utf-8'))
 if d.get('format')!=fmt or d.get('ready') is not True: raise ValueError(path)
 return d

def build(indirect:Path,resolver:Path):
 i=load(indirect,'SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/4')
 r=load(resolver,'SHIFT.P1B.HDVehicle4330GetProcAddressStorageCoverage/1')
 assert i['surface']['p1b_exact_carrier_count']==15
 assert i['surface']['composed_coverage_class_count']==7
 assert i['surface']['bounded_exact_carrier_hit_count']==0
 assert r['surface']['physical_getprocaddress_callsite_count']==101
 assert r['surface']['all_statically_reachable_imported_getprocaddress_result_lineages_covered'] is True
 assert r['surface']['bounded_static_getprocaddress_carrier_identity_hit_count']==0
 assert i['adjudication']['external_provider_count']==r['adjudication']['external_provider_count']==7
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1B / P1.3B',
  'upstream_contracts':[i['format'],r['format']],
  'surface':{
    'p1b_exact_carrier_count':15,
    'nonresolver_bounded_seed_class_count':7,
    'nonresolver_bounded_exact_carrier_hit_count':0,
    'statically_reachable_getprocaddress_callsite_count':101,
    'statically_reachable_getprocaddress_carrier_identity_hit_count':0,
    'composed_bounded_seed_domain_count':8,
    'composed_bounded_exact_carrier_hit_count':0,
  },
  'adjudication':{
    'bounded_runtime_pointer_seed_domains_composed':True,
    'bounded_runtime_pointer_seed_can_produce_exact_internal_carrier':False,
    'runtime_generated_or_copied_function_pointers_ruled_out':False,
    'generic_function_pointer_stores_copies_ruled_out':False,
    'runtime_computed_carrier_pointers_ruled_out':False,
    'runtime_copied_or_encoded_carrier_pointers_ruled_out':False,
    'memory_table_derived_carrier_pointers_ruled_out':False,
    'runtime_patching_or_generated_code_ruled_out':False,
    'indirect_entry_into_carriers_ruled_out':False,
    'manager_374_join_to_hdvehicle_4330_complete':False,
    'last_literal_0x004b86cf_rejected':False,
    'p1_3_control_producer_complete':False,
    'external_provider_count':7,
  },
  'limits':[
    'This composes only already-bounded exact-carrier seed/materialization classes plus statically reachable imported-GetProcAddress storage.',
    'Runtime-created resolver aliases, unrelated runtime-populated pointer tables, cross-block/table-derived arithmetic, runtime patching and opaque external pointer sources remain open.'
  ],
  'next_step':'Inventory unrelated runtime-populated function-pointer tables and cross-block/table-derived carrier synthesis before promoting global store/copy or indirect-entry gates.'
 }

def main():
 p=argparse.ArgumentParser(); p.add_argument('--indirect',type=Path,required=True); p.add_argument('--resolver',type=Path,required=True); p.add_argument('--output',type=Path); a=p.parse_args(); d=build(a.indirect,a.resolver); t=json.dumps(d,indent=2,sort_keys=True)+'\n'; a.output.write_text(t,encoding='utf-8') if a.output else print(t,end='')
if __name__=='__main__': main()
