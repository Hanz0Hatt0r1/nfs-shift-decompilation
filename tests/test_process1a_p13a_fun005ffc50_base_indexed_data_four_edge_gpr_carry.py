import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_base_indexed_data_four_edge_gpr_carry.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_base_indexed_data_four_edge_gpr_carry.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_cfg',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def helper():
 s=importlib.util.spec_from_file_location('h',ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_base_indexed_data_implicit_push_pop.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_taken_edge_can_reach_indirect_call():
 m=mod();h=helper();rows=[(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'je','0x1010'),(0x1009,'xor','eax,eax'),(0x100b,'ret',''),(0x1010,'nop',''),(0x1011,'call','eax')];r=m.scan_cfg(rows,h);assert r['tainted_register_indirect_transfer_count']==1 and r['maximum_direct_edge_depth_reached']==1
def test_fifth_direct_edge_is_not_followed():
 m=mod();h=helper();rows=[(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'jmp','0x1010'),(0x1010,'jmp','0x1020'),(0x1020,'jmp','0x1030'),(0x1030,'jmp','0x1040'),(0x1040,'jmp','0x1050'),(0x1050,'call','eax')];r=m.scan_cfg(rows,h);assert r['tainted_register_indirect_transfer_count']==0 and r['maximum_direct_edge_depth_reached']==4 and r['termination_reason_counts']['jmp_stop']==1
def test_dependency_erasing_clobber_stops_path():
 m=mod();h=helper();rows=[(0x1000,'mov','esi,0xb81000'),(0x1005,'mov','eax,DWORD PTR [esi]'),(0x1007,'xor','eax,eax'),(0x1009,'call','eax')];r=m.scan_cfg(rows,h);assert r['tainted_register_indirect_transfer_count']==0 and r['termination_reason_counts']=={'all_taint_dead':1}
def test_unknown_base_not_seeded():
 m=mod();h=helper();r=m.scan_cfg([(0x1000,'mov','eax,DWORD PTR [esi+4]'),(0x1004,'call','eax')],h);assert r['base_indexed_data_load_count']==0
def test_retail_inventory():
 i=data()['inventory'];assert i['base_indexed_data_load_count']==63 and i['unique_effective_address_count']==51;assert i['explored_state_count']==1107 and i['unique_direct_branch_site_count']==186;assert i['direct_edge_traversal_count_by_depth']=={'1':88,'2':130,'3':107,'4':67};assert i['maximum_direct_edge_depth_reached']==4 and i['tainted_register_indirect_transfer_count']==0;assert i['termination_reason_counts']=={'all_taint_dead':118,'branch_stop':15,'call_stop':67,'jmp_stop':8,'return_or_trap':8,'window_exhausted':19}
def test_global_gate_stays_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_base_indexed_data_up_to_four_direct_cfg_edge_gpr_carry_subset_complete'] is True;assert a['base_indexed_data_cfg_carried_register_indirect_transfer_found'] is False;assert a['base_indexed_inter_block_carry_ruled_out'] is False;assert a['unbounded_multi_edge_or_phi_reconstruction_ruled_out'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['external_provider_count']==7
