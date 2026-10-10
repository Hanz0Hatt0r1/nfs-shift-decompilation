import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_fnstenv_stack_restore.py';E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_fnstenv_stack_restore.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_fnstenv',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_inventory_exact_four_decodes_two_stack():
 p=data();i=p['fnstenv_inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50FnstenvStackRestore/1'
 assert i['decoded_instruction_count']==2847850 and i['total_fnstenv_or_fstenv_count']==4 and i['stack_esp_fnstenv_count']==2 and i['non_stack_fnstenv_count']==2
 assert [x['site'] for x in i['rows']]==['0x004177e4','0x0050d063','0x00913763','0x00913a1b']
def test_stack_sequences_save_modify_restore_without_gpr_extract():
 p=data();s=p['stack_restore_semantics'];assert len(p['stack_restore_sequences'])==2
 assert s['saved_environment_size_bytes']==28 and s['gpr_load_from_saved_environment_between_fnstenv_and_fldenv'] is False
 assert s['saved_environment_restored_with_fldenv'] is True and s['stack_storage_released_immediately_after_restore'] is True and s['fun005ffc50_pointer_extracted'] is False
def test_machine_ranges_and_upstream_are_pinned():
 p=data();m=mod();assert p['authority']['retail_executable_sha256']==m.SHA and p['authority']['upstream_contract']==m.UPSTREAM
 for n,(s,e,h) in m.RANGES.items():
  r=p['authority']['machine_ranges'][n];assert r=={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
def test_narrow_gate_keeps_other_entry_classes_fail_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_fnstenv_stack_restore_subset_complete'] is True
 assert a['stack_fnstenv_fun005ffc50_reconstruction_found'] is False and a['stack_fnstenv_fun005ffc50_indirect_entry_found'] is False
 for k in ['non_stack_fnstenv_decodes_ruled_out_as_entry','other_pic_or_fnstenv_entry_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
