import importlib.util,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun005ffc50_static_memory_stack_reconstruction.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_static_memory_stack_reconstruction.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_5ffc50_memstack',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_synthetic_readonly_image_seed_reconstruction_is_detected():
 m=mod();blob=bytearray(0x404);struct.pack_into('<I',blob,0x400,0x005ff000)
 lines=[
  '  00500000: a1 00 10 40 00 mov eax,DWORD PTR ds:0x401000\n',
  '  00500005: 05 50 0c 00 00 add eax,0xc50\n',
  '  0050000a: ff d0 call eax\n']
 n,loads,rm,sm,xf=m.scan_lines(lines,bytes(blob));assert n==3 and len(loads)==1
 assert rm==[{'site':'0x00500005','register':'eax','instruction':'add eax,0xc50'}]
 assert sm==[] and xf==[{'site':'0x0050000a','kind':'call','source_kind':'register','source':'eax'}]
def test_synthetic_ebp_stack_reconstruction_is_detected():
 m=mod();lines=[
  '  00500000: 55 push ebp\n','  00500001: 8b ec mov ebp,esp\n','  00500003: 83 ec 08 sub esp,0x8\n',
  '  00500006: c7 45 fc 00 f0 5f 00 mov DWORD PTR [ebp-0x4],0x5ff000\n',
  '  0050000d: 81 45 fc 50 0c 00 00 add DWORD PTR [ebp-0x4],0xc50\n',
  '  00500014: 8b 45 fc mov eax,DWORD PTR [ebp-0x4]\n','  00500017: ff d0 call eax\n']
 n,loads,rm,sm,xf=m.scan_lines(lines,b'');assert n==7 and loads==[]
 assert sm==[{'site':'0x0050000d','stack_offset_from_region_entry':-8,'instruction':'add DWORD PTR [ebp-0x4],0xc50'}]
 assert rm==[{'site':'0x00500014','register':'eax','instruction':'mov eax,DWORD PTR [ebp-0x4]'}]
 assert xf==[{'site':'0x00500017','kind':'call','source_kind':'register','source':'eax'}]
def test_retail_image_and_stack_surface_is_zero():
 p=data();assert p['format']=='SHIFT.P1A.P13AFun005ffc50StaticMemoryStackReconstruction/1'
 assert p['scope']['decoded_instruction_count']==2847850
 i=p['inventory'];assert i['image_backed_dword_load_count']==484
 assert i['image_backed_dword_load_count_by_section']=={'.rdata':483,'.text':1}
 assert i['exact_target_register_materialization_count']==0 and i['exact_target_stack_materialization_count']==0 and i['exact_target_indirect_transfer_count']==0
 assert i['register_materializations']==[] and i['stack_materializations']==[] and i['indirect_transfers']==[]
def test_narrow_gate_keeps_runtime_memory_fail_closed():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_readonly_image_and_explicit_stack_reconstruction_subset_complete'] is True
 assert a['readonly_image_backed_fun005ffc50_reconstruction_found'] is False
 assert a['explicit_stack_local_fun005ffc50_reconstruction_found'] is False
 assert a['readonly_image_or_stack_fun005ffc50_indirect_transfer_found'] is False
 for k in ['writable_memory_or_runtime_fun005ffc50_entry_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
