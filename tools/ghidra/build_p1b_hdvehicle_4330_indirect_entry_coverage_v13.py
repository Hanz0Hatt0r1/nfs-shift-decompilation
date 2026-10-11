#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PREV=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v12.json'
ADD=ROOT/'evidence'/'p1b_hdvehicle_4330_base_indexed_direct_callee_provenance.json'
FORMAT='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/13'
def build():
 p=json.loads(PREV.read_text(encoding='utf-8')); a=json.loads(ADD.read_text(encoding='utf-8'))
 assert p['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/12'
 assert a['format']=='SHIFT.P1B.HDVehicle4330BaseIndexedDirectCalleeProvenance/1'
 assert p['surface']['composed_coverage_class_count']==16
 assert a['surface']['escape_count']==5 and a['surface']['classified_escape_count']==5
 assert a['surface']['unclassified_escape_count']==0
 assert a['surface']['indirect_call_or_jump_through_escape_value_count']==0
 return {'format':FORMAT,'version':13,'ready':True,'owner':'Process 1B / P1.3B aggregate integration','supersedes':p['format'],'upstream_contracts':[p['format'],a['format']],
 'surface':{'p1b_exact_carrier_count':15,'previous_bounded_coverage_class_count':16,'composed_coverage_class_count':17,'bounded_exact_carrier_hit_count':0,'incoming_indirect_navigation_edge_count':19500,'incoming_indirect_unresolved_target_count':19500,'base_indexed_direct_call_argument_escape_count':5,'base_indexed_direct_call_argument_escape_classified_count':5,'base_indexed_direct_call_argument_escape_unclassified_count':0,'base_indexed_direct_callee_indirect_transfer_count':0,'base_indexed_direct_callee_string_data_escape_count':5,'coverage_addition':{'class':'base/index-addressed writable .data direct-callee argument provenance','escape_count':5,'classified_count':5,'unclassified_count':0,'indirect_transfer_count':0,'exact_carrier_hit_count':0}},
 'adjudication':{'bounded_indirect_entry_coverage_composed':True,'bounded_indirect_entry_exact_4330_carrier_hit_found':False,'base_indexed_implicit_stack_carrier_surface_included':True,'base_indexed_direct_callee_provenance_included':True,'base_indexed_direct_call_escape_data_provenance_complete':True,'base_indexed_direct_call_escape_can_be_callable_target_in_bounded_callee_surface':False,'base_indexed_inter_block_carry_remains_open':True,'base_indexed_runtime_or_alias_provenance_remains_open':True,'remaining_incoming_entry_blocker_is_unresolved_nonstatic_indirect_target_recovery':True,'indirect_entry_into_carriers_ruled_out':False,'runtime_generated_or_copied_function_pointers_ruled_out':False,'generic_function_pointer_stores_copies_ruled_out':False,'runtime_patching_or_generated_code_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
 'limits':['This supersedes /12 by classifying all five exact direct-call argument escapes found by the implicit-stack carrier scan.','All five are consumed as NUL-terminated string/data on the bounded selected callee chains, with zero CALL/JMP through the escape value.','Inter-block/phi carry, aliases, heap/runtime mutation, generated/copied pointers and unrelated indirect target classes remain open.','The 19,500 navigation-index unresolved edges remain a capability metric, not a decrementing remainder counter.'],'next_step':'Bound inter-block carry and remaining alias/runtime target classes before promoting the global indirect-entry gate.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);x=ap.parse_args();t=json.dumps(build(),indent=2,sort_keys=True)+'\n';x.output.write_text(t,encoding='utf-8') if x.output else print(t,end='');return 0
if __name__=='__main__':raise SystemExit(main())
