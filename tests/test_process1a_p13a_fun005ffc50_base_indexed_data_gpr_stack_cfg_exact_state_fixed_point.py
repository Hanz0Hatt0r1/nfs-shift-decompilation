import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_base_indexed_data_gpr_stack_cfg_exact_state_fixed_point.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_base_indexed_data_gpr_stack_cfg_exact_state_fixed_point.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_stackcfg',AN);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_committed_evidence_contract_and_counts():
 d=json.loads(EV.read_text());r=d['inventory']
 assert d['format']=='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataGprStackCfgExactStateFixedPoint/1'
 assert (r['base_indexed_data_load_count'],r['unique_effective_address_count'])==(63,51)
 assert (r['exact_gpr_stack_state_count'],r['duplicate_state_prune_count'],r['unique_direct_branch_site_count'])==(1106,80,201)
def test_stack_cfg_inventory_is_stable():
 r=json.loads(EV.read_text())['inventory']
 assert (r['unique_stack_carry_branch_successor_count'],r['maximum_tracked_stack_cells'])==(8,3)
 assert (r['unique_stack_spill_event_count'],r['unique_stack_reload_event_count'])==(2,1)
 assert (r['unique_tainted_push_event_count'],r['unique_tainted_pop_reload_event_count'])==(35,0)
def test_no_indirect_transfer_and_semantic_termination_counts():
 r=json.loads(EV.read_text())['inventory']
 assert r['tainted_register_indirect_transfer_count']==0
 assert r['termination_reason_counts']=={'all_taint_dead':104,'call_stop':70,'return_or_trap':7}
def test_positive_synthetic_branch_spill_reload_to_call():
 m=module();h,base,stack=m.mods()
 rows=[(0x1000,'mov','eax,0xb82304'),(0x1005,'mov','ecx,DWORD PTR [eax]'),(0x1007,'mov','DWORD PTR [ebp-0x28],ecx'),(0x100a,'je','0x1010'),(0x100c,'mov','edx,DWORD PTR [ebp-0x28]'),(0x100f,'call','edx'),(0x1010,'ret','')]
 r=m.scan(rows,h,base,stack);assert r['tainted_register_indirect_transfer_count']==1 and r['unique_stack_reload_event_count']==1
def test_branch_without_reload_remains_negative():
 m=module();h,base,stack=m.mods();rows=[(0x1000,'mov','eax,0xb82304'),(0x1005,'mov','ecx,DWORD PTR [eax]'),(0x1007,'mov','DWORD PTR [ebp-0x28],ecx'),(0x100a,'je','0x1010'),(0x100c,'xor','ecx,ecx'),(0x100e,'ret',''),(0x1010,'ret','')]
 assert m.scan(rows,h,base,stack)['tainted_register_indirect_transfer_count']==0
def test_global_gates_remain_fail_closed():
 a=json.loads(EV.read_text())['adjudication']
 assert a['base_indexed_inter_block_carry_ruled_out'] is True and a['base_indexed_stack_state_across_cfg_edges_ruled_out'] is True
 for k in ['base_indexed_writable_sources_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','callbacks_and_indirect_entry_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
