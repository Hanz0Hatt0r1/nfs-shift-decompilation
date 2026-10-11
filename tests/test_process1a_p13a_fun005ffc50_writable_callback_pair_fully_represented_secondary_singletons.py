import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_fully_represented_secondary_singletons.py';EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_fully_represented_secondary_singletons.json'
def module():s=importlib.util.spec_from_file_location('p1a_secondary_singletons',AN);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_counts():
 i=data()['inventory'];assert i['fully_represented_two_gpr_site_count']==27;assert i['observation_count']==32;assert i['non_singleton_secondary_observation_count']==0
def test_singleton_values():
 i=data()['inventory'];assert i['secondary_singleton_site_value_counts']=={'0x00000000':6,'0x00aa9b60':21};assert i['secondary_singleton_observation_value_counts']=={'0x00000000':9,'0x00aa9b60':23}
def test_mnemonic_surface():assert data()['inventory']['mnemonic_site_counts']=={'cmp':19,'lea':3,'mov':5}
def test_expected_site_count():assert len(module().EXPECTED_SITES)==27
def test_narrow_gates():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_fully_represented_secondary_singleton_subset_complete'];assert a['writable_callback_pair_fully_represented_secondary_values_all_singleton'];assert not a['writable_callback_pair_fully_represented_two_gpr_frontier_empty']
def test_global_gates_false():
 a=data()['adjudication'];
 for k in ['writable_callback_pair_single_top_frontier_empty','writable_callback_pair_may_state_top_frontier_empty','writable_callback_pair_multi_edge_computed_alias_sources_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
