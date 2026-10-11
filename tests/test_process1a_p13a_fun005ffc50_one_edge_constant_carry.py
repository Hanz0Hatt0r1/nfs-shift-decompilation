import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_one_edge_constant_carry.py';E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_one_edge_constant_carry.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_oneedge',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_taken_edge_reconstructs_target():
 m=mod();rows=[(0x1000,'mov','eax,0x5ff000'),(0x1005,'jne','0x1010'),(0x1007,'ret',''),(0x1010,'add','eax,0xc50'),(0x1015,'call','eax')]
 r=m.scan(rows);assert len(r['materializations'])==1 and r['materializations'][0]['site']=='0x00001010';assert len(r['indirect_transfers'])==1 and r['indirect_transfers'][0]['site']=='0x00001015'
def test_synthetic_fallthrough_edge_reconstructs_target():
 m=mod();rows=[(0x1000,'mov','ecx,0x5ff000'),(0x1005,'je','0x1020'),(0x1007,'add','ecx,0xc50'),(0x100c,'jmp','ecx'),(0x1020,'ret','')]
 r=m.scan(rows);assert len(r['materializations'])==1 and r['materializations'][0]['successor']=='fallthrough';assert len(r['indirect_transfers'])==1
def test_retail_one_edge_inventory_is_zero_for_target():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50OneEdgeConstantCarry/1';assert p['scope']['decoded_instruction_count']==2847850
 assert i['branch_seed_count']==17745 and i['successor_basic_block_path_count']==30181 and i['simulated_successor_instruction_count']==159630 and i['max_successor_block_instruction_count']==225
 assert i['materializations']==[] and i['indirect_transfers']==[]
def test_narrow_gate_keeps_multi_edge_and_runtime_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_one_direct_cfg_edge_constant_carry_subset_complete'] is True
 assert a['one_edge_fun005ffc50_materialization_found'] is False and a['one_edge_fun005ffc50_indirect_transfer_found'] is False
 for k in ['multi_edge_or_phi_reconstruction_ruled_out','return_value_fun005ffc50_provenance_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
