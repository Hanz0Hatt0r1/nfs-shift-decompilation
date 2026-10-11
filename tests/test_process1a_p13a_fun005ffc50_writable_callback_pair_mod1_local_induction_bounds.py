import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_mod1_local_induction_bounds.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_mod1_local_induction_bounds.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_mod1_bounds',AN); assert s and s.loader; m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def data(): return json.loads(EV.read_text())
def test_retail_counts():
 r=data()['inventory']; assert r['decoded_instruction_count']==2847850; assert r['upstream_mod1_site_count']==7; assert r['locally_bounded_site_count']==4; assert r['remaining_mod1_site_count']==3
def test_exact_remaining_sites():
 assert data()['inventory']['remaining_mod1_sites']==['0x00503328','0x0050334b','0x005d5621']
def test_local_ranges_do_not_cover_targets():
 m=module()
 for x in data()['inventory']['locally_bounded_sites']:
  lo=int(x['effective_address_min'],16); hi=int(x['effective_address_max'],16); assert all(not(lo<=t<=hi) for t in m.TARGETS); assert x['callback_target_possible'] is False
def test_eax_loop_is_exact_zero_at_use():
 x=data()['inventory']['locally_bounded_sites'][0]; assert x['site']=='0x004b9124'; assert (x['primary_min'],x['primary_max'])==(0,0)
def test_edi_loop_bounds():
 xs={x['site']:x for x in data()['inventory']['locally_bounded_sites']}; assert xs['0x006084d0']['primary_max']==254; assert xs['0x00608539']['primary_max']==255; assert xs['0x0060853f']['primary_max']==255
def test_global_gates_remain_fail_closed():
 a=data()['adjudication']; assert a['p13a_fun005ffc50_writable_callback_pair_mod1_local_induction_bound_subset_complete'] is True; assert a['writable_callback_pair_mod1_local_induction_exclusion_found'] is True
 for k in ['writable_callback_pair_target_compatible_frontier_empty','writable_callback_pair_indirect_or_alias_writers_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','p1_3_control_producer_complete']: assert a[k] is False
 assert a['external_provider_count']==7
