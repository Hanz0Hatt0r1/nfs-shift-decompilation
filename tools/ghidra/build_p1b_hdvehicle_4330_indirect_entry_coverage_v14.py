#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PREV=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v13.json'
ADD=ROOT/'evidence'/'p1b_hdvehicle_4330_base_indexed_direct_cfg_carry.json'
FORMAT='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/14'
def build():
 p=json.loads(PREV.read_text(encoding='utf-8')); a=json.loads(ADD.read_text(encoding='utf-8'))
 assert p['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/13'
 assert a['format']=='SHIFT.P1B.HDVehicle4330BaseIndexedDirectCFGCarry/1'
 assert p['surface']['composed_coverage_class_count']==17
 i=a['inventory']; assert (i['base_indexed_data_load_count'],i['direct_cfg_carried_load_count'],i['tainted_register_indirect_transfer_count'],i['fixed_point_maxout_count'])==(63,44,0,0)
 return {'format':FORMAT,'version':14,'ready':True,'owner':'Process 1B / P1.3B aggregate integration','supersedes':p['format'],'upstream_contracts':[p['format'],a['format']],
 'surface':{'p1b_exact_carrier_count':15,'previous_bounded_coverage_class_count':17,'composed_coverage_class_count':18,'bounded_exact_carrier_hit_count':0,'incoming_indirect_navigation_edge_count':19500,'incoming_indirect_unresolved_target_count':19500,'base_indexed_direct_cfg_carried_load_count':44,'base_indexed_direct_cfg_branch_state_event_count':207,'base_indexed_direct_cfg_branch_site_count':199,'base_indexed_direct_cfg_tainted_indirect_transfer_count':0,'base_indexed_direct_cfg_direct_call_boundary_count':56,'base_indexed_direct_cfg_indirect_jump_boundary_count':11,'coverage_addition':{'class':'base/index-addressed writable .data direct-CFG GPR carry','carried_load_count':44,'branch_state_event_count':207,'branch_site_count':199,'tainted_indirect_transfer_count':0,'direct_call_boundary_count':56,'indirect_jump_boundary_count':11,'exact_carrier_hit_count':0}},
 'adjudication':{'bounded_indirect_entry_coverage_composed':True,'bounded_indirect_entry_exact_4330_carrier_hit_found':False,'base_indexed_direct_callee_provenance_included':True,'base_indexed_direct_cfg_gpr_carry_subset_included':True,'base_indexed_direct_cfg_tainted_register_indirect_transfer_found':False,'base_indexed_direct_call_boundaries_remain_open':True,'base_indexed_indirect_jump_successors_remain_open':True,'base_indexed_inter_block_carry_globally_ruled_out':False,'base_indexed_runtime_or_alias_provenance_remains_open':True,'remaining_incoming_entry_blocker_is_unresolved_nonstatic_indirect_target_recovery':True,'indirect_entry_into_carriers_ruled_out':False,'runtime_generated_or_copied_function_pointers_ruled_out':False,'generic_function_pointer_stores_copies_ruled_out':False,'runtime_patching_or_generated_code_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
 'limits':['This supersedes /13 by composing a direct-CFG GPR carry fixed-point subset over the same 63 base/index writable-data loads.','Forty-four loads cross at least one direct basic-block edge; no path dispatches CALL/JMP through the tainted register within the modeled direct-CFG surface.','Fifty-six direct-call boundaries and eleven indirect-jump successor boundaries remain explicit open provenance frontiers.','Stack/alias/heap/runtime/generated-pointer classes remain open, and the 19,500 navigation-index unresolved edges remain a capability metric.'],'next_step':'Classify the 11 indirect-jump successor boundaries and relevant direct-call live-taint boundaries before promoting any global inter-block or indirect-entry gate.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);x=ap.parse_args();t=json.dumps(build(),indent=2,sort_keys=True)+'\n';x.output.write_text(t,encoding='utf-8') if x.output else print(t,end='');return 0
if __name__=='__main__':raise SystemExit(main())
