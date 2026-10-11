#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PREV=ROOT/'evidence'/'p1b_hdvehicle_4330_indirect_entry_coverage_v9.json'
ADD=ROOT/'evidence'/'p1b_hdvehicle_4330_base_indexed_writable_near_transfer.json'
FORMAT='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/10'
def build():
 p=json.loads(PREV.read_text()); a=json.loads(ADD.read_text())
 assert p['format']=='SHIFT.P1B.HDVehicle4330IndirectEntryCoverage/9'
 assert a['format']=='SHIFT.P1B.HDVehicle4330BaseIndexedWritableNearTransfer/1'
 assert p['surface']['composed_coverage_class_count']==13
 assert a['surface']['same_register_indirect_transfer_count']==0
 return {'format':FORMAT,'version':10,'ready':True,'owner':'Process 1B / P1.3B aggregate integration','supersedes':p['format'],'upstream_contracts':[p['format'],a['format']],
 'surface':{'p1b_exact_carrier_count':15,'previous_bounded_coverage_class_count':13,'composed_coverage_class_count':14,'bounded_exact_carrier_hit_count':0,'incoming_indirect_navigation_edge_count':19500,'incoming_indirect_unresolved_target_count':19500,'base_indexed_writable_data_load_count':63,'base_indexed_unique_effective_address_count':51,'base_indexed_same_register_indirect_transfer_count':0,'base_indexed_exact_carrier_hit_count':0,'coverage_addition':{'class':'base/index-addressed writable .data same-register near-transfer recovery','load_count':63,'unique_effective_address_count':51,'exact_carrier_hit_count':0}},
 'adjudication':{'bounded_indirect_entry_coverage_composed':True,'bounded_indirect_entry_exact_4330_carrier_hit_found':False,'base_indexed_writable_same_register_near_transfer_subset_included':True,'base_indexed_copy_transform_spill_interblock_remain_open':True,'remaining_incoming_entry_blocker_is_unresolved_nonstatic_indirect_target_recovery':True,'indirect_entry_into_carriers_ruled_out':False,'runtime_generated_or_copied_function_pointers_ruled_out':False,'generic_function_pointer_stores_copies_ruled_out':False,'runtime_patching_or_generated_code_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
 'limits':['This supersedes /9 by adding only the target-agnostic base/indexed writable same-register 16-instruction near-transfer negative subset.','Copies/transforms, stack spill/reload, inter-block carry, aliases, runtime mutation and other indirect target classes remain open.','The 19,500 navigation-index unresolved edges remain a capability metric, not a decrementing remainder counter.'],
 'next_step':'Follow copied/transformed/spilled/inter-block base-indexed writable values and alias writers before promoting any global indirect-entry gate.'}
def main():
 q=argparse.ArgumentParser();q.add_argument('--output',type=Path);a=q.parse_args();t=json.dumps(build(),indent=2,sort_keys=True)+'\n';a.output.write_text(t) if a.output else print(t,end='');return 0
if __name__=='__main__': raise SystemExit(main())