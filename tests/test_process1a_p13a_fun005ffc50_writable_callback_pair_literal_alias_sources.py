import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AN=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_writable_callback_pair_literal_alias_sources.py'
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_literal_alias_sources.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_cb_literal_alias',AN);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EV.read_text())
def test_exact_literal_inventory():
 i=data()['inventory'];assert (i['0x00b87b80']['raw_exact_va_literal_count'],i['0x00b87b7c']['raw_exact_va_literal_count'])==(29,54)
def test_all_exact_literals_are_classified():
 for x in data()['inventory'].values():assert x['raw_exact_va_literal_count']==x['decoded_operand_literal_count'] and x['unclassified_exact_literal_count']==0
def test_expected_operand_classes():
 i=data()['inventory'];assert i['0x00b87b80']['classification_counts']=={'snapshot_load':1,'transfer':26,'write':2};assert i['0x00b87b7c']['classification_counts']=={'snapshot_load':1,'transfer':51,'write':2}
def test_classifier_accepts_only_known_direct_forms():
 m=module();s=0x00b87b80
 assert m.classify('call','DWORD PTR ds:0xb87b80',s,0x1000)=='transfer'
 assert m.classify('mov','ds:0xb87b80,eax',s,0x1000)=='write'
 assert m.classify('mov','eax,ds:0xb87b80',s,0x00a7fa5c)=='snapshot_load'
 assert m.classify('push','0xb87b80',s,0x1000)=='other'
def test_narrow_gate_is_promoted():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_exact_literal_alias_source_subset_complete'] is True;assert a['writable_callback_pair_exact_slot_address_literals_fully_classified'] is True;assert a['writable_callback_pair_exact_slot_address_literal_alias_source_found'] is False
def test_global_alias_gates_stay_fail_closed():
 a=data()['adjudication'];
 for k in ['writable_callback_pair_indirect_or_alias_writers_ruled_out','register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','callbacks_and_indirect_entry_ruled_out','stored_or_escaped_aliases_ruled_out','p1_3_control_producer_complete']:assert a[k] is False
 assert a['external_provider_count']==7
