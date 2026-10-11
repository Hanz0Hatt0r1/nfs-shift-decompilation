import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_computed_alias_sources.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_computed_alias_sources.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_cb_comp_alias',AN);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_inventory_is_zero():
 r=data()['inventory'];assert r['decoded_instruction_count']==2847850;assert r['computed_exact_slot_register_formation_count']==0;assert r['computed_exact_slot_memory_operand_count']==0
def test_positive_synthetic_computed_register_and_use():
 m=module();rows=[(0x1000,'mov','eax,0xb87b00'),(0x1005,'add','eax,0x80'),(0x1008,'mov','ecx,DWORD PTR [eax]')];r=m.scan(rows);assert r['computed_exact_slot_register_formation_count']==1;assert r['computed_exact_slot_memory_operand_count']==1
def test_branch_boundary_kills_constant_state():
 m=module();rows=[(0x1000,'mov','eax,0xb87b00'),(0x1005,'jmp','0x1010'),(0x1010,'add','eax,0x80'),(0x1013,'mov','ecx,DWORD PTR [eax]')];r=m.scan(rows);assert r['computed_exact_slot_register_formation_count']==0;assert r['computed_exact_slot_memory_operand_count']==0
def test_callee_saved_survives_call_but_volatile_does_not():
 m=module();r=m.scan([(0x1000,'mov','ebx,0xb87b00'),(0x1005,'call','0x2000'),(0x100a,'add','ebx,0x80')]);assert r['computed_exact_slot_register_formation_count']==1
 r=m.scan([(0x1000,'mov','eax,0xb87b00'),(0x1005,'call','0x2000'),(0x100a,'add','eax,0x80')]);assert r['computed_exact_slot_register_formation_count']==0
def test_narrow_gate_only():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_straight_line_computed_alias_source_subset_complete'] is True;assert a['writable_callback_pair_straight_line_computed_exact_alias_found'] is False
def test_global_alias_gates_remain_false():
 a=data()['adjudication'];
 for k in ['writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
