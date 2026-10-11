import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_may_state_widening_frontier.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_may_state_widening_frontier.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_cb_widen',AN);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_frontier_counts():
 i=data()['inventory'];assert i['joined_cfg_entry_count']==116695;assert i['processed_entry_count']==452675;assert i['top_memory_use_site_count']==2793;assert i['exact_callback_slot_hit_count']==0
def test_merge_widens_after_cap():
 m=module();a=frozenset(range(m.CAP));b=frozenset({m.CAP});assert m.merge_val(a,b) is m.TOP
def test_merge_keeps_small_exact_union():
 m=module();assert m.merge_val(frozenset({1,2}),frozenset({2,3}))==frozenset({1,2,3})
def test_synthetic_top_memory_use_is_reported():
 m=module();rows=[]
 for n in range(m.CAP+1):
  base=0x1000+n*0x20;rows += [(base,'mov',f'eax,0x{0x2000+n:x}'),(base+5,'jmp','0x1200')]
 rows += [(0x1200,'mov','ecx,DWORD PTR [eax]')]
 rows.sort();r=m.scan(rows);assert r['top_memory_use_site_count']>=1;assert r['exact_callback_slot_hit_count']==0
def test_exact_target_hit_is_not_hidden_by_widening():
 m=module();rows=[(0x1000,'mov','eax,0xb87b80'),(0x1005,'jne','0x1010'),(0x1007,'ret',''),(0x1010,'mov','ecx,DWORD PTR [eax]')];r=m.scan(rows);assert r['exact_callback_slot_hit_count']>=1
def test_global_gates_remain_fail_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_may_state_widening_frontier_subset_complete'] is True;assert a['writable_callback_pair_may_state_top_frontier_empty'] is False;assert a['writable_callback_pair_multi_edge_computed_alias_sources_ruled_out'] is False;assert a['writable_callback_pair_indirect_or_alias_writers_ruled_out'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['external_provider_count']==7
