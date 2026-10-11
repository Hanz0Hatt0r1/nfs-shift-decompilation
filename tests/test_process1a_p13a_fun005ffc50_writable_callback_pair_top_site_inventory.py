import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_top_site_inventory.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_top_site_inventory.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_top_inv',AN);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_frontier_partition():
 i=data()['inventory'];assert i['top_memory_use_site_count']==2793;assert i['top_memory_use_observation_count']==6401;assert i['unique_memory_expression_count']==893;assert i['site_class_counts']=={'contains_two_top':15,'finite_combination_overflow_only':2,'mixed_single_top_and_finite_overflow':90,'single_top_only':2686}
def test_retail_top_register_site_counts():
 assert data()['inventory']['top_register_site_counts']=={'eax':701,'ebp':21,'ebx':320,'ecx':352,'edi':550,'edx':111,'esi':751}
def test_static_site_partition_is_total():
 c=data()['inventory']['site_class_counts'];assert sum(c.values())==2793
def test_expected_mnemonics_cover_all_sites():
 assert sum(data()['inventory']['site_mnemonic_counts'].values())==2793
def test_inventory_gate_only():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_top_site_inventory_subset_complete'] is True;assert a['writable_callback_pair_top_site_frontier_classified'] is True;assert a['writable_callback_pair_may_state_top_frontier_empty'] is False
def test_global_gates_remain_false():
 a=data()['adjudication'];
 for k in ['writable_callback_pair_multi_edge_computed_alias_sources_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
