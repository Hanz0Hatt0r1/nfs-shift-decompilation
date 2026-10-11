import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_mod4_local_induction_bounds.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_mod4_local_induction_bounds.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_mod4_bounds',AN);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_counts():
 r=data()['inventory'];assert r['decoded_instruction_count']==2847850;assert r['locally_bounded_site_count']==4;assert r['remaining_target_compatible_site_count']==7
def test_expected_sites():
 assert [x['site'] for x in data()['inventory']['locally_bounded_sites']]==['0x00572951','0x00878f82','0x00a64930','0x00a64e40']
def test_stride_and_bounds():
 xs=data()['inventory']['locally_bounded_sites'];assert xs[0]['primary_max']==252;assert all(x['primary_stride']==4 for x in xs);assert [x['primary_max'] for x in xs[1:]]==[1020,1020,1020]
def test_ranges_exclude_targets():
 m=module()
 for x in data()['inventory']['locally_bounded_sites']:
  lo=int(x['effective_address_min'],16);hi=int(x['effective_address_max'],16);assert all(not(lo<=t<=hi) for t in m.TARGETS);assert x['callback_target_possible'] is False
def test_remaining_frontier_exact():
 assert data()['inventory']['remaining_target_compatible_sites']==['0x00503328','0x0050334b','0x005d5621','0x007a6e9e','0x007a6ea5','0x007f25a0','0x0080b696']
def test_global_gates_remain_false():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_mod4_local_induction_bound_subset_complete'] is True;assert a['writable_callback_pair_mod4_local_induction_exclusion_found'] is True
 for k in ['writable_callback_pair_target_compatible_frontier_empty','writable_callback_pair_indirect_or_alias_writers_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
