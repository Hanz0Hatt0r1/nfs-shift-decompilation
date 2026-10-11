import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_four_edge_constant_carry.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_four_edge_constant_carry.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_fouredge',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_three_edge_path_reconstructs_target_and_calls_it():
 m=mod();rows=[(0x1000,'mov','eax,0x5ff000'),(0x1005,'jne','0x1010'),(0x1007,'jmp','0x1020'),(0x1010,'jmp','0x1020'),(0x1020,'add','eax,0xc50'),(0x1025,'je','0x1030'),(0x1027,'ret',''),(0x1030,'call','eax')]
 r=m.scan(rows);assert r['materializations'] and r['materializations'][0]['site']=='0x00001020';assert r['indirect_transfers'] and r['indirect_transfers'][0]['site']=='0x00001030' and r['indirect_transfers'][0]['depth']==3
def test_synthetic_call_boundary_terminates_carried_state():
 m=mod();rows=[(0x1000,'mov','eax,0x5ff000'),(0x1005,'jne','0x1010'),(0x1007,'ret',''),(0x1010,'call','0x2000'),(0x1015,'add','eax,0xc50'),(0x101a,'jmp','eax')]
 r=m.scan(rows);assert r['materializations']==[] and r['indirect_transfers']==[]
def test_retail_four_edge_inventory_is_zero_for_target():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50FourEdgeConstantCarry/1';assert p['scope']['decoded_instruction_count']==2847850
 assert i['branch_seed_count']==17745 and i['initial_successor_path_count']==30181 and i['max_edges']==4
 assert i['evaluated_state_block_count']==84674 and i['evaluated_state_block_count_by_depth']=={'1':29768,'2':21280,'3':17555,'4':16071}
 assert i['simulated_instruction_count']==443364 and i['max_scanned_block_instruction_count']==226 and i['unique_start_state_count']==84674
 assert i['materializations']==[] and i['indirect_transfers']==[]
def test_narrow_gate_keeps_unbounded_phi_return_and_runtime_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_up_to_four_direct_cfg_edge_constant_carry_subset_complete'] is True
 assert a['four_edge_fun005ffc50_materialization_found'] is False and a['four_edge_fun005ffc50_indirect_transfer_found'] is False
 for k in ['unbounded_multi_edge_or_phi_reconstruction_ruled_out','return_value_fun005ffc50_provenance_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
