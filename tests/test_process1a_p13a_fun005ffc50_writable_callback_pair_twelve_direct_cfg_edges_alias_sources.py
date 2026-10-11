import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_twelve_direct_cfg_edges_alias_sources.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_twelve_direct_cfg_edges_alias_sources.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_cb_12',AN);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_inventory_counts():
 r=data()['inventory'];assert r['decoded_instruction_count']==2847850;assert r['unique_exact_state_count']==1014242;assert r['unique_exact_state_count_by_depth']['12']==158354
def test_retail_has_no_exact_slot_hits():
 r=data()['inventory'];assert r['computed_exact_slot_register_formation_count']==0;assert r['computed_exact_slot_memory_operand_count']==0
def test_synthetic_exact_formation_is_detected():
 m=module();rows=[(0x1000,'mov','eax,0xb87b00'),(0x1005,'jmp','0x1010'),(0x1010,'add','eax,0x80')];r=m.scan(rows,max_depth=12);assert r['computed_exact_slot_register_formation_count']==1
def test_synthetic_memory_use_is_detected():
 m=module();rows=[(0x1000,'mov','ebx,0xb87b80'),(0x1005,'jne','0x1010'),(0x1007,'ret',''),(0x1010,'mov','eax,DWORD PTR [ebx]')];r=m.scan(rows,max_depth=12);assert r['computed_exact_slot_memory_operand_count']==1
def test_depth_bound_is_explicit():
 m=module();assert m.MAX_DEPTH==12;assert set(m.EXPECTED_STATES)=={str(i) for i in range(1,13)}
def test_only_narrow_gate_is_promoted():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_up_to_twelve_direct_cfg_edges_computed_alias_source_subset_complete'] is True;assert a['writable_callback_pair_multi_edge_computed_alias_sources_ruled_out'] is False;assert a['writable_callback_pair_indirect_or_alias_writers_ruled_out'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['external_provider_count']==7
