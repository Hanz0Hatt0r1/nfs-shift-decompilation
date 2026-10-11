#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PREV=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v15.json'
ADD=ROOT/'evidence'/'p1b_hdvehicle_4330_source_slot_exact_address_surface.json'
FORMAT='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/16'
def build():
 p=json.loads(PREV.read_text(encoding='utf-8'));a=json.loads(ADD.read_text(encoding='utf-8'))
 assert p['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/15';assert a['format']=='SHIFT.P1B.HDVehicle4330SourceSlotExactAddressSurface/1';assert p['surface']['composed_coverage_class_count']==19
 s=a['surface'];assert s['total_exact_source_slot_address_dword_occurrence_count']==6 and s['total_static_alias_getter_direct_call_site_count']==3 and s['total_static_alias_getter_function_address_dword_occurrence_count']==0
 return {'format':FORMAT,'version':16,'ready':True,'owner':'Process 1B / P1.3B aggregate integration','supersedes':p['format'],'upstream_contracts':[p['format'],a['format']],
 'surface':{'p1b_exact_carrier_count':15,'previous_bounded_coverage_class_count':19,'composed_coverage_class_count':20,'bounded_exact_carrier_hit_count':0,'incoming_indirect_navigation_edge_count':19500,'incoming_indirect_unresolved_target_count':19500,'source_slot_exact_address_dword_occurrence_count':6,'source_slot_static_alias_getter_direct_call_site_count':3,'source_slot_static_alias_getter_function_address_dword_occurrence_count':0,'coverage_addition':{'class':'selected source-slot exact address and static alias-getter entry surface','source_slot_address_dword_occurrence_count':6,'alias_getter_direct_call_site_count':3,'alias_getter_function_address_dword_occurrence_count':0}},
 'adjudication':{'bounded_indirect_entry_coverage_composed':True,'bounded_indirect_entry_exact_4330_carrier_hit_found':False,'exact_source_slot_address_literal_surface_included':True,'exact_source_slot_alias_getter_static_entry_surface_included':True,'source_slot_alias_getter_function_address_taken_found':False,'computed_or_runtime_alias_surface_complete':False,'runtime_or_alias_writer_provenance_complete':False,'memory_derived_indirect_call_target_identity_complete':False,'indirect_entry_into_carriers_ruled_out':False,'runtime_generated_or_copied_function_pointers_ruled_out':False,'generic_function_pointer_stores_copies_ruled_out':False,'runtime_patching_or_generated_code_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
 'limits':['This supersedes /15 by composing only the exact whole-image source-slot address literal surface and static entry surface of the two exact alias getters.','The exact source-slot addresses occur six times total, and the alias getters have three direct callsites with zero raw function-address dword occurrences.','Computed/copied/runtime aliases and caller write/escape semantics remain open, so runtime target identity and global incoming indirect entry remain fail-closed.'],'next_step':'Classify the three direct alias-getter caller paths for write/escape behavior, then continue computed alias/runtime writer provenance.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);a=ap.parse_args();t=json.dumps(build(),indent=2,sort_keys=True)+'\n';a.output.write_text(t,encoding='utf-8') if a.output else print(t,end='');return 0
if __name__=='__main__':raise SystemExit(main())
