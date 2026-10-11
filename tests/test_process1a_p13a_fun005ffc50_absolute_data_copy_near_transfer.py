import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_absolute_data_copy_near_transfer.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_absolute_data_copy_near_transfer.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_abs_copy',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_register_copy_then_indirect_call_is_detected():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'mov','ecx,eax'),(0x1007,'call','ecx')])
 assert r['copy_event_count']==1 and r['copied_register_indirect_transfer_count']==1
 h=r['copied_register_indirect_transfers'][0]
 assert h['origin_register']=='eax' and h['transfer_register']=='ecx' and h['transfer_site']=='0x00001007'
def test_synthetic_copy_survives_origin_clobber():
 m=mod();r=m.scan_rows([(0x1000,'mov','eax,ds:0xb81000'),(0x1005,'mov','ecx,eax'),(0x1007,'xor','eax,eax'),(0x1009,'call','ecx')])
 assert r['copied_register_indirect_transfer_count']==1 and r['copied_register_indirect_transfers'][0]['transfer_register']=='ecx'
def test_synthetic_xchg_transfers_taint():
 m=mod();r=m.scan_rows([(0x1000,'mov','edx,ds:0xb81004'),(0x1006,'xchg','edx,edi'),(0x1008,'jmp','edi')])
 assert r['copy_event_count']==1 and r['copy_events'][0]['copy_kind']=='xchg'
 assert r['copied_register_indirect_transfer_count']==1
def test_retail_copy_inventory_is_exact_and_has_no_transfer():
 p=data();i=p['inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50AbsoluteDataCopyNearTransfer/1'
 assert i['decoded_instruction_count']==2847850 and i['absolute_data_load_count']==1786 and i['unique_absolute_data_slot_count']==434
 assert i['copy_event_count']==10 and i['copied_load_count']==10
 assert i['copy_count_by_pair']=={'eax->ecx':2,'eax->edx':1,'ecx->eax':1,'ecx->edx':2,'edi->eax':1,'edi->ecx':2,'edx->ecx':1}
 assert i['copied_register_indirect_transfer_count']==0 and i['tainted_register_indirect_transfer_count']==0
 assert i['termination_reason_counts']=={'all_tainted_registers_clobbered':411,'other_control_transfer':1357,'window_exhausted':18}
 assert p['upstream_termination_delta']=={'other_control_transfer':2,'register_clobber_to_all_tainted_clobbered':-2,'window_exhausted':0}
 assert i['copy_events'][0]['copy_site']=='0x005ec427' and i['copy_events'][-1]['copy_site']=='0x00a22fa9'
def test_narrow_gate_keeps_global_writable_and_callback_closure_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_absolute_data_register_copy_near_transfer_subset_complete'] is True
 assert a['absolute_data_copied_register_indirect_transfer_found'] is False
 for k in ['register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','return_value_fun005ffc50_provenance_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
