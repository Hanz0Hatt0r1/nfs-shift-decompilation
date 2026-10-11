import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_trivial_constant_return_producers.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_trivial_constant_return_producers.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_retprod',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_constant_return_then_postcall_reconstruction_is_detected():
 m=mod();rows=[(0x1000,'mov','eax,0x5ff000'),(0x1005,'ret',''),(0x2000,'call','0x1000'),(0x2005,'add','eax,0xc50'),(0x200a,'call','eax')]
 r=m.scan(rows);assert r['trivial_constant_return_producer_count']==1 and r['trivial_constant_return_callsite_count']==1
 assert r['materializations'] and r['materializations'][0]['site']=='0x00002005';assert r['indirect_transfers'] and r['indirect_transfers'][0]['site']=='0x0000200a'
def test_synthetic_branched_callee_is_deliberately_out_of_scope():
 m=mod();rows=[(0x1000,'mov','eax,0x5ff000'),(0x1005,'jne','0x1010'),(0x1007,'ret',''),(0x1010,'ret',''),(0x2000,'call','0x1000'),(0x2005,'add','eax,0xc50')]
 r=m.scan(rows);assert r['trivial_constant_return_producer_count']==0 and r['materializations']==[] and r['indirect_transfers']==[]
def test_retail_trivial_constant_return_inventory_is_zero_for_target():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50TrivialConstantReturnProducers/1';assert p['scope']['decoded_instruction_count']==2847850
 assert i['direct_call_target_count']==25666 and i['trivial_constant_return_producer_count']==280 and i['trivial_constant_return_callsite_count']==859
 assert i['unique_return_constant_count']==41 and i['post_call_simulated_instruction_count']==3045
 assert i['materializations']==[] and i['indirect_transfers']==[]
def test_narrow_gate_keeps_general_return_and_runtime_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_trivial_constant_return_producer_subset_complete'] is True
 assert a['trivial_return_fun005ffc50_materialization_found'] is False and a['trivial_return_fun005ffc50_indirect_transfer_found'] is False
 for k in ['return_value_fun005ffc50_provenance_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
