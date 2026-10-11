import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_base_indexed_data_gpr_cfg_exact_state_fixed_point.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_base_indexed_data_gpr_cfg_exact_state_fixed_point.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_fp',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def helpers():
 m=mod();h=m.helper();return m,h,h.helper()
def test_cycle_is_pruned_and_call_seen():
 m,h,b=helpers();rows=[(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'je','0x1010'),(0x1009,'call','eax'),(0x1010,'jmp','0x1007')];r=m.scan_fixed_point(rows,h);assert r['tainted_register_indirect_transfer_count']==1 and r['cycle_or_join_duplicate_state_prune_count']>=1
def test_dependency_erasing_clobber_stops():
 m,h,b=helpers();r=m.scan_fixed_point([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'xor','eax,eax'),(0x1009,'call','eax')],h);assert r['tainted_register_indirect_transfer_count']==0 and r['termination_reason_counts']=={'all_taint_dead':1}
def test_direct_loop_without_transfer_converges():
 m,h,b=helpers();r=m.scan_fixed_point([(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'jmp','0x1007')],h);assert r['tainted_register_indirect_transfer_count']==0 and r['cycle_or_join_duplicate_state_prune_count']==1
def test_unknown_base_not_seeded():
 m,h,b=helpers();r=m.scan_fixed_point([(0x1000,'mov','eax,DWORD PTR [esi+4]'),(0x1004,'call','eax')],h);assert r['base_indexed_data_load_count']==0
def test_retail_inventory():
 i=data()['inventory'];assert i['base_indexed_data_load_count']==63 and i['unique_effective_address_count']==51;assert i['exact_gpr_state_count']==1063 and i['cycle_or_join_duplicate_state_prune_count']==78;assert i['unique_direct_branch_site_count']==199 and i['maximum_states_for_single_seed']==83;assert i['tainted_register_indirect_transfer_count']==0;assert i['termination_reason_counts']=={'all_taint_dead':107,'call_stop':67,'return_or_trap':6}
def test_adjudication_stays_narrow():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_base_indexed_data_gpr_cfg_exact_state_fixed_point_subset_complete'] is True;assert a['base_indexed_gpr_inter_block_carry_ruled_out'] is True;assert a['base_indexed_inter_block_carry_ruled_out'] is False;assert a['base_indexed_stack_state_across_cfg_edges_ruled_out'] is False;assert a['unbounded_multi_edge_or_phi_reconstruction_ruled_out'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['external_provider_count']==7
