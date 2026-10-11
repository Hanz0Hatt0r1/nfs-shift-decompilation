import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_target_compatible_congruence_frontier.py';EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_target_compatible_congruence_frontier.json'
def module():s=importlib.util.spec_from_file_location('p1a_frontier',AN);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_classes():
 i=data()['inventory'];assert i['target_compatible_site_count']==15;assert i['terminal_congruence_class_counts']=={'0 mod 1':7,'0 mod 4':5,'0 mod 8':2,'4 mod 8':1}
def test_mnemonics():assert data()['inventory']['terminal_mnemonic_counts']=={'cmp':7,'lea':3,'mov':5}
def test_mod1_is_largest_class():assert data()['inventory']['terminal_congruence_class_counts']['0 mod 1']==7
def test_sites_are_complete():assert len(data()['inventory']['sites'])==15 and len({x['site'] for x in data()['inventory']['sites']})==15
def test_narrow_gate():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_target_compatible_congruence_frontier_subset_complete'];assert a['writable_callback_pair_target_compatible_frontier_requires_provenance_refinement']
def test_globals_fail_closed():
 a=data()['adjudication'];
 for k in ['writable_callback_pair_fully_represented_two_gpr_frontier_empty','writable_callback_pair_single_top_frontier_empty','writable_callback_pair_may_state_top_frontier_empty','writable_callback_pair_multi_edge_computed_alias_sources_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
