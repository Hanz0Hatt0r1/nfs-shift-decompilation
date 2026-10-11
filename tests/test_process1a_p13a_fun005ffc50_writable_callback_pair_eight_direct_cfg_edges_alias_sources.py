import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_eight_direct_cfg_edges_alias_sources.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_eight_direct_cfg_edges_alias_sources.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_cb_8edge_alias',AN);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_inventory():
 r=data()['inventory'];assert r['decoded_instruction_count']==2847850;assert r['successor_seed_count_by_depth']=={'1':35329,'2':39184,'3':47455,'4':58362,'5':72068,'6':88419,'7':105925,'8':125644};assert r['unique_exact_state_count_by_depth']=={'1':34890,'2':36265,'3':42307,'4':50536,'5':60521,'6':72035,'7':83429,'8':97087};assert r['unique_exact_state_count']==477070;assert r['computed_exact_slot_register_formation_count']==0;assert r['computed_exact_slot_memory_operand_count']==0
def test_positive_eighth_edge_formation():
 m=module();rows=[(0x1000,'mov','eax,0xb87b00')]+[(0x1010+i*0x10,'jmp',f'0x{0x1020+i*0x10:x}') for i in range(8)]+[(0x1090,'add','eax,0x80')];assert m.scan(rows)['computed_exact_slot_register_formation_count']==1
def test_seven_edge_bound_does_not_claim_eighth_edge():
 m=module();rows=[(0x1000,'mov','eax,0xb87b00')]+[(0x1010+i*0x10,'jmp',f'0x{0x1020+i*0x10:x}') for i in range(8)]+[(0x1090,'add','eax,0x80')];assert m.scan(rows,7)['computed_exact_slot_register_formation_count']==0
def test_unknown_target_not_seeded():
 m=module();assert m.scan([(0x1000,'mov','eax,0xb87b00'),(0x1005,'jmp','0x9999')])['unique_exact_state_count']==0
def test_narrow_gate_only():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_up_to_eight_direct_cfg_edges_computed_alias_source_subset_complete'] is True;assert a['writable_callback_pair_up_to_eight_direct_cfg_edges_computed_exact_alias_found'] is False
def test_global_alias_gates_remain_false():
 a=data()['adjudication'];
 for k in ['writable_callback_pair_multi_edge_computed_alias_sources_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
