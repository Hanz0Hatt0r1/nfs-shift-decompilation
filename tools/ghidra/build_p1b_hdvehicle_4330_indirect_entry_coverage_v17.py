#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PREV=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v16.json'
ADD=ROOT/'evidence'/'p1b_hdvehicle_4330_alias_getter_direct_consumer_slot0.json'
FORMAT='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/17'
def build():
 p=json.loads(PREV.read_text(encoding='utf-8'));a=json.loads(ADD.read_text(encoding='utf-8'))
 assert p['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/16';assert a['format']=='SHIFT.P1B.HDVehicle4330AliasGetterDirectConsumerSlot0Writer/1';assert p['surface']['composed_coverage_class_count']==20
 s=a['surface'];assert s['direct_alias_getter_callsite_count']==3 and s['slot0_write_or_pointer_escape_count']==0
 return {'format':FORMAT,'version':17,'ready':True,'owner':'Process 1B / P1.3B aggregate integration','supersedes':p['format'],'upstream_contracts':[p['format'],a['format']],
 'surface':{'p1b_exact_carrier_count':15,'previous_bounded_coverage_class_count':20,'composed_coverage_class_count':21,'bounded_exact_carrier_hit_count':0,'incoming_indirect_navigation_edge_count':19500,'incoming_indirect_unresolved_target_count':19500,'direct_alias_getter_callsite_count':3,'direct_alias_getter_slot0_write_or_pointer_escape_count':0,'direct_alias_getter_nonstack_direct_memory_write_count':0,'coverage_addition':{'class':'direct alias-getter consumer slot0 writer closure','direct_getter_callsite_count':3,'slot0_write_or_pointer_escape_count':0,'nonstack_direct_memory_write_count':0}},
 'adjudication':{'bounded_indirect_entry_coverage_composed':True,'bounded_indirect_entry_exact_4330_carrier_hit_found':False,'direct_alias_getter_consumer_slot0_writer_subset_included':True,'direct_alias_getter_consumer_slot0_write_or_pointer_escape_found':False,'computed_or_runtime_alias_surface_complete':False,'runtime_or_alias_writer_provenance_complete':False,'memory_derived_indirect_call_target_identity_complete':False,'indirect_entry_into_carriers_ruled_out':False,'runtime_generated_or_copied_function_pointers_ruled_out':False,'generic_function_pointer_stores_copies_ruled_out':False,'runtime_patching_or_generated_code_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
 'limits':['This supersedes /16 by composing only the three direct alias-getter caller paths with respect to slot0/table-pointer writes and pointer escapes.','Those callers expose only nonzero object-field addresses to helpers and contain zero non-stack direct memory writes; slot0 itself is neither written nor passed by address.','Computed/copied/runtime aliases, indirect getter entry and unrelated writers remain open, so exact runtime target identity and global incoming indirect entry remain fail-closed.'],'next_step':'Continue computed/copied/runtime alias provenance for 0x00b83dc0 and 0x00b83ec0, then return to remaining live-taint call boundaries.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);a=ap.parse_args();t=json.dumps(build(),indent=2,sort_keys=True)+'\n';a.output.write_text(t,encoding='utf-8') if a.output else print(t,end='');return 0
if __name__=='__main__':raise SystemExit(main())
