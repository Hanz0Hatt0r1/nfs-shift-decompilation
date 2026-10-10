#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, hashlib
from pathlib import Path
FORMAT='SHIFT.P1B.HDVehicle4330GetProcAddressRegisterLoadedResultLineage/1'
EXPECTED_SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
EXPECTED_SIZE=8801792
EXPECTED_PROVIDER_COUNT=7
V2=Path(__file__).with_name('analyze_p1b_hdvehicle_4330_getprocaddress_static_resolution_v2.py')

def load(path):
 s=importlib.util.spec_from_file_location('m',path); m=importlib.util.module_from_spec(s); assert s.loader; s.loader.exec_module(m); return m

def analyze(exe:Path,v2_path:Path=V2):
 v2=load(v2_path); d=v2.analyze(exe); s=d['getprocaddress_surface']
 if s['register_loaded_callsite_count']!=89 or [x['callsite_count'] for x in s['register_loaded_families']]!=[2,4,5,2,6,67,3]: raise ValueError('resolver surface drift')
 data=exe.read_bytes(); sha=hashlib.sha256(data).hexdigest()
 if sha!=EXPECTED_SHA or len(data)!=EXPECTED_SIZE: raise ValueError('retail authority mismatch')
 b=v2.load_base(); ins=b.parse_objdump(exe); by={r['address']:r for r in ins}
 def expect(addr,mn,contains):
  r=by.get(addr)
  if not r or r['mnemonic']!=mn or contains not in r['operands']: raise ValueError(f'pattern drift 0x{addr:08x}')
 for a,c in [(0x90abff,'[esi+0x1f8]'),(0x90ac0f,'[esi+0x1fc]')]: expect(a,'mov',c)
 for a,c in [(0x90aec0,'0xc321dc'),(0x90aecd,'0xc321e0'),(0x90aeda,'0xc321e4'),(0x90aeee,'0xc321e8')]: expect(a,'mov',c)
 for a,c in [(0x91c0d4,'0xc329fc'),(0x91c0e9,'0xc32a00'),(0x91c0f6,'0xc32a04'),(0x91c12e,'0xc32a0c'),(0x91c144,'0xc32a08')]: expect(a,'mov',c)
 for a,c in [(0x96dabb,'0xc5e80c'),(0x96dac9,'0xc5e810')]: expect(a,'mov',c)
 for a,c in [(0x99a009,'[esi+0x29c]'),(0x99a02f,'[esi+0x2a0]'),(0x99a0d7,'[ebx]'),(0x99a0e8,'[ebx]'),(0x99a0f7,'[esi+0x2ac]'),(0x99a11a,'[esi+0x29c]')]: expect(a,'mov',c)
 f=s['register_loaded_families'][5]; start=int(f['first_callsite'],16); end=int(f['last_callsite'],16)
 calls=[(i,r) for i,r in enumerate(ins) if start<=r['address']<=end and r['mnemonic']=='call' and r['operands']=='esi']
 offsets=[]
 for i,r in calls:
  found=None
  for x in ins[i+1:i+4]:
   if x['mnemonic']=='mov' and x['operands'].endswith(',eax') and x['operands'].startswith('dword ptr [edi'):
    op=x['operands'].split(',',1)[0]
    if op=='dword ptr [edi]': found=0
    else: found=int(op.split('+0x',1)[1].split(']',1)[0],16)
    break
  if found is None: raise ValueError(f'OpenAL sink missing after 0x{r["address"]:08x}')
  offsets.append(found)
 if offsets!=list(range(0,0x10c,4)): raise ValueError('OpenAL table offsets drift')
 expect(0xa62364,'mov','[esp+0x20],eax'); expect(0xa623c0,'mov','edi,eax'); expect(0xa623c6,'mov','ebx,eax')
 families=[
  {'loadsite':'0x0090abf7','module':'KERNEL32.DLL','callsite_count':2,'sink_kind':'object_fields','distinct_sink_count':2},
  {'loadsite':'0x0090aeac','module':'KERNEL32.DLL','callsite_count':4,'sink_kind':'absolute_globals','distinct_sink_count':4},
  {'loadsite':'0x0091c0b0','module':'USER32.DLL','callsite_count':5,'sink_kind':'encoded_absolute_globals','distinct_sink_count':5},
  {'loadsite':'0x0096daa2','module':'wnaspi32.dll','callsite_count':2,'sink_kind':'absolute_globals','distinct_sink_count':2},
  {'loadsite':'0x00999fe7','module':'dsound.dll','callsite_count':6,'sink_kind':'object_fields_with_fallback_overwrite','distinct_sink_count':4},
  {'loadsite':'0x009a7e40','module':'openal32.dll','callsite_count':67,'sink_kind':'caller_provided_function_table','distinct_sink_count':67},
  {'loadsite':'0x00a62354','module':'gdi32.dll','callsite_count':3,'sink_kind':'stack_register_helper_transient','distinct_sink_count':1},
 ]
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1B / P1.3B','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'retail_file_size':len(data),'retail_bytes_are_machine_authority':True},'surface':{'register_loaded_callsite_count':89,'family_count':7,'families':families,'external_module_count':6,'all_resolved_values_external_dll_exports':True,'exact_internal_p1b_carrier_identity_hit_count':0,'openal_table_slot_count':67,'openal_table_first_offset':'0x0','openal_table_last_offset':'0x108'},'adjudication':{'cfg_aware_register_loaded_result_lineage_subset_complete':True,'resolver_populated_bounded_storage_surface_complete':True,'resolver_populated_storage_can_hold_exact_internal_p1b_carrier':False,'runtime_generated_or_copied_function_pointers_ruled_out':False,'generic_function_pointer_stores_copies_ruled_out':False,'dynamic_getprocaddress_resolution_ruled_out':False,'runtime_patching_or_generated_code_ruled_out':False,'indirect_entry_into_carriers_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':EXPECTED_PROVIDER_COUNT},'limits':['Closes only the seven CFG-aware static IAT-load families. Runtime-created resolver aliases, external function pointers, unrelated runtime-populated tables and opaque helper resolution remain open.'],'next_step':'Compose direct-IAT, wrapper-output and CFG-aware register-loaded result lineage into bounded GetProcAddress storage coverage.'}

def main():
 p=argparse.ArgumentParser(); p.add_argument('exe',type=Path); p.add_argument('--v2-analyzer',type=Path,default=V2); p.add_argument('--output',type=Path); a=p.parse_args(); d=analyze(a.exe,a.v2_analyzer); t=json.dumps(d,indent=2,sort_keys=True)+'\n'; a.output.write_text(t) if a.output else print(t,end='')
if __name__=='__main__': main()
