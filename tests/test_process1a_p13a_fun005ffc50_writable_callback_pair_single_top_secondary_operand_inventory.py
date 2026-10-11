import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_single_top_secondary_operand_inventory.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_single_top_secondary_operand_inventory.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_cb_secondary',AN);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_retail_partition():
 i=data()['inventory'];assert i['single_top_site_count']==2686;assert i['expression_arity_site_counts']=={'1':1564,'2':1122};assert i['two_gpr_secondary_absent_site_count']==1095;assert i['two_gpr_secondary_fully_represented_site_count']==27
def test_missing_secondary_register_counts():
 assert data()['inventory']['missing_secondary_register_site_counts']=={'eax':293,'ebp':37,'ebx':81,'ecx':232,'edi':81,'edx':265,'esi':106}
def test_classify_two_gpr_missing_secondary():
 m=module()
 class M: REGS={'eax','ecx'}; TOP=object()
 items=[{'expr':'eax+ecx*1','state':{'eax':M.TOP,'ecx':None}}]
 r=m.classify_site(items,M);assert r['arity']==2 and r['secondary_absent'];assert r['top_registers']=={'eax'};assert r['missing_registers']=={'ecx'}
def test_classify_two_gpr_represented_secondary():
 m=module()
 class M: REGS={'eax','ecx'}; TOP=object()
 items=[{'expr':'eax+ecx*1','state':{'eax':M.TOP,'ecx':frozenset({1,2})}}]
 r=m.classify_site(items,M);assert r['arity']==2 and not r['secondary_absent']
def test_narrow_gates():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_single_top_secondary_operand_inventory_subset_complete'];assert a['writable_callback_pair_single_top_two_gpr_secondary_absence_classified'];assert not a['writable_callback_pair_single_top_secondary_operand_frontier_empty']
def test_global_gates_remain_false():
 a=data()['adjudication'];
 for k in ['writable_callback_pair_single_top_frontier_empty','writable_callback_pair_may_state_top_frontier_empty','writable_callback_pair_multi_edge_computed_alias_sources_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
