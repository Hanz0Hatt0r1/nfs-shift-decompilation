import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_single_top_congruence_refinement.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_single_top_congruence_refinement.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_cb_single_top_cong',AN);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_refinement_counts():
 i=data()['inventory'];assert i['upstream_single_top_only_site_count']==2686;assert i['congruence_excluded_site_count']==290;assert i['unresolved_single_top_site_count']==2396
 assert i['refinement_class_counts']=={'congruence_rules_out_target':290,'target_still_possible':1145,'unknown_value':1244,'unseen_in_refined_fixed_point':7}
def test_widened_congruence_preserves_residue():
 m=module();v=m.from_values(range(0,36,4));assert m.is_congruence(v);assert v[2]==4;assert v[1]==0
def test_congruence_can_rule_out_both_callback_slots():
 m=module();v=('congruence',2,4);assert m.target_possible(v,{0x00b87b80,0x00b87b7c}) is False
def test_congruence_keeps_compatible_target_unresolved():
 m=module();v=('congruence',0,4);assert m.target_possible(v,{0x00b87b80,0x00b87b7c}) is True
def test_unknown_operand_stays_unresolved():
 m=module();assert m.target_possible(None,{0x00b87b80,0x00b87b7c}) is None
def test_narrow_gate_only():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_single_top_congruence_refinement_subset_complete'] is True
 assert a['writable_callback_pair_single_top_frontier_empty'] is False
 for k in ['writable_callback_pair_may_state_top_frontier_empty','writable_callback_pair_multi_edge_computed_alias_sources_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
