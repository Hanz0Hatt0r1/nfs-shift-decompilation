import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_fully_represented_secondary_congruence_fold.py';EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_fully_represented_secondary_congruence_fold.json'
def module():s=importlib.util.spec_from_file_location('p1a_fold',AN);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_partition():
 i=data()['inventory'];assert i['folded_secondary_site_count']==27;assert i['class_counts']=={'ruled_out':12,'target_possible':15};assert i['ruled_out_site_count']==12;assert i['target_possible_site_count']==15
def test_ruled_out_sites_are_expected():
 assert data()['inventory']['ruled_out_sites']==['0x00572957','0x0057295e','0x00572965','0x00878f88','0x00878f8f','0x00878f96','0x00a64936','0x00a6493d','0x00a64944','0x00a64e46','0x00a64e4d','0x00a64e54']
def test_residue_classes():assert data()['inventory']['ruled_out_congruence_residue_observation_counts']=={'1 mod 4':30,'2 mod 4':27,'3 mod 4':27}
def test_classify_helper():
 m=module();assert m.classify([{'target_possible':False}])=='ruled_out';assert m.classify([{'target_possible':True}])=='target_possible';assert m.classify([{'target_possible':None}])=='unknown'
def test_narrow_gate():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_fully_represented_secondary_congruence_fold_subset_complete'];assert a['writable_callback_pair_fully_represented_secondary_congruence_exclusion_found'];assert not a['writable_callback_pair_fully_represented_two_gpr_frontier_empty']
def test_globals_fail_closed():
 a=data()['adjudication'];
 for k in ['writable_callback_pair_single_top_frontier_empty','writable_callback_pair_may_state_top_frontier_empty','writable_callback_pair_multi_edge_computed_alias_sources_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
