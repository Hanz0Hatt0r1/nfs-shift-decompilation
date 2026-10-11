import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_mod1_zero_guard_exclusion.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_mod1_zero_guard_exclusion.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_mod1_zero_guard',AN);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_counts():
 r=data()['inventory'];assert r['decoded_instruction_count']==2847850;assert r['upstream_target_compatible_site_count']==7;assert r['zero_guard_excluded_site_count']==1;assert r['remaining_target_compatible_site_count']==6
def test_exact_excluded_site():
 x=data()['inventory']['zero_guard_excluded_sites'][0];assert x['site']=='0x005d5621';assert x['secondary_singleton']=='0x00aa9b60';assert x['base_section']=='.rdata';assert x['base_first_byte']=='0x00'
def test_guard_skips_site():
 x=data()['inventory']['zero_guard_excluded_sites'][0];assert x['guard_site']=='0x005d560c';assert x['guard_taken_target']=='0x005d562b';assert x['site_reachable_under_secondary_singleton'] is False;assert x['callback_target_possible'] is False
def test_remaining_frontier_exact():
 assert data()['inventory']['remaining_target_compatible_sites']==['0x00503328','0x0050334b','0x007a6e9e','0x007a6ea5','0x007f25a0','0x0080b696']
def test_va_reader_contract_excludes_targets():
 m=module();x=data()['inventory']['zero_guard_excluded_sites'][0];assert int(x['secondary_singleton'],16)==m.BASE;assert all(t!=m.BASE for t in m.TARGETS)
def test_global_gates_remain_fail_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_mod1_zero_guard_exclusion_subset_complete'] is True;assert a['writable_callback_pair_mod1_zero_guard_exclusion_found'] is True
 for k in ['writable_callback_pair_target_compatible_frontier_empty','writable_callback_pair_indirect_or_alias_writers_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
