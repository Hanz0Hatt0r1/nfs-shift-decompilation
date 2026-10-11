import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_two_direct_cfg_edges_alias_sources.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_two_direct_cfg_edges_alias_sources.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_cb_twoedge',AN);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_inventory_zero_aliases():
 r=data()['inventory'];assert r['first_edge_successor_seed_count']==35329;assert r['second_edge_successor_seed_count']==39184;assert r['unique_exact_state_count_by_depth']=={'1':34890,'2':36265};assert r['unique_exact_state_count']==71155;assert r['computed_exact_slot_register_formation_count']==0;assert r['computed_exact_slot_memory_operand_count']==0
def test_two_edge_taken_path_can_form_target():
 m=module();rows=[(0x1000,'mov','eax,0xb87b00'),(0x1005,'jmp','0x1010'),(0x1010,'nop',''),(0x1011,'jmp','0x1020'),(0x1020,'add','eax,0x80'),(0x1023,'mov','ecx,DWORD PTR [eax]')];r=m.scan(rows);assert r['computed_exact_slot_register_formation_count']==1;assert r['computed_exact_slot_memory_operand_count']==1
def test_three_edge_path_is_out_of_scope():
 m=module();rows=[(0x1000,'mov','eax,0xb87b00'),(0x1005,'jmp','0x1010'),(0x1010,'jmp','0x1020'),(0x1020,'jmp','0x1030'),(0x1030,'add','eax,0x80'),(0x1033,'mov','ecx,DWORD PTR [eax]')];r=m.scan(rows);assert r['computed_exact_slot_memory_operand_count']==0
def test_unknown_state_is_not_seeded():
 m=module();rows=[(0x1000,'mov','eax,DWORD PTR [ebx]'),(0x1005,'jmp','0x1010'),(0x1010,'jmp','0x1020'),(0x1020,'add','eax,0x80')];r=m.scan(rows);assert r['first_edge_successor_seed_count']==0
def test_narrow_gate_only():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_up_to_two_direct_cfg_edges_computed_alias_source_subset_complete'] is True;assert a['writable_callback_pair_up_to_two_direct_cfg_edges_computed_exact_alias_found'] is False;assert a['writable_callback_pair_multi_edge_computed_alias_sources_ruled_out'] is False
def test_global_alias_gates_remain_false():
 a=data()['adjudication'];
 for k in ['writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
