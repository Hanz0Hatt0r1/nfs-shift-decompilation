#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PREV=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v14.json'
ADD=ROOT/'evidence'/'p1b_hdvehicle_4330_memory_derived_call_target_provenance.json'
FORMAT='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/15'
def build():
 p=json.loads(PREV.read_text(encoding='utf-8')); a=json.loads(ADD.read_text(encoding='utf-8'))
 assert p['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/14'
 assert a['format']=='SHIFT.P1B.HDVehicle4330BaseIndexedMemoryDerivedCallTargetProvenance/1'
 assert p['surface']['composed_coverage_class_count']==18
 s=a['surface']; assert s['target_derived_call_count']==2 and s['bounded_callable_target_exact_carrier_hit_count']==0
 return {'format':FORMAT,'version':15,'ready':True,'owner':'Process 1B / P1.3B aggregate integration','supersedes':p['format'],'upstream_contracts':[p['format'],a['format']],
 'surface':{'p1b_exact_carrier_count':15,'previous_bounded_coverage_class_count':18,'composed_coverage_class_count':19,'bounded_exact_carrier_hit_count':0,'incoming_indirect_navigation_edge_count':19500,'incoming_indirect_unresolved_target_count':19500,'memory_derived_call_count':2,'bounded_static_initializer_table_pointer_count':2,'bounded_static_initializer_callable_target_count':2,'bounded_static_initializer_callable_target_exact_carrier_hit_count':0,'bounded_static_initializer_callable_targets':['0x00553260','0x00553a90'],'coverage_addition':{'class':'memory-derived call target bounded static/initializer provenance','target_derived_call_count':2,'table_pointer_count':2,'callable_target_count':2,'exact_carrier_hit_count':0}},
 'adjudication':{'bounded_indirect_entry_coverage_composed':True,'bounded_indirect_entry_exact_4330_carrier_hit_found':False,'base_indexed_memory_derived_indirect_call_target_found':True,'bounded_static_initializer_target_provenance_included':True,'bounded_static_initializer_target_can_hit_exact_p1b_carrier':False,'memory_derived_indirect_call_target_identity_complete':False,'runtime_or_alias_writer_provenance_complete':False,'base_indexed_direct_call_boundaries_remain_open':True,'base_indexed_indirect_call_boundaries_remain_open':True,'base_indexed_inter_block_carry_globally_ruled_out':False,'indirect_entry_into_carriers_ruled_out':False,'runtime_generated_or_copied_function_pointers_ruled_out':False,'generic_function_pointer_stores_copies_ruled_out':False,'runtime_patching_or_generated_code_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
 'limits':['This supersedes /14 by composing only the bounded image-initial and exact visible initializer/reset writer subset for the two positive memory-derived calls.','The bounded table pointers 0x00acdd68/0x00acdd70 yield callable targets 0x00553a90/0x00553260 and neither is a canonical P1B carrier.','Computed aliases, arbitrary runtime mutation, heap/object replacement and other writers remain open; exact runtime target identity and global incoming indirect entry remain fail-closed.'],'next_step':'Bound computed/alias/runtime writers for 0x00b83dc0 and 0x00b83ec0, then classify remaining call boundaries before any global indirect-entry promotion.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);a=ap.parse_args();t=json.dumps(build(),indent=2,sort_keys=True)+'\n';a.output.write_text(t,encoding='utf-8') if a.output else print(t,end='');return 0
if __name__=='__main__':raise SystemExit(main())
