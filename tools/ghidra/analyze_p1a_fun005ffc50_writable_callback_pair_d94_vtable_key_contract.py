#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94VtableKeyContract/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94HelperInitializer/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s): return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace'); assert p.stdout
 out=[]
 for line in p.stdout:
  m=I.match(line)
  if m: out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 err=p.stderr.read() if p.stderr else ''
 if p.wait(): raise RuntimeError(err)
 return out
def req(by,a,m,o):
 if by.get(a)!=(m,o): raise AssertionError((hex(a),by.get(a),(m,o)))
def analyze(exe:Path, upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA: raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_d94_helper_initializer_subset_complete'):
  raise AssertionError('upstream incomplete')
 rows=dis(exe); by={a:(m,o) for a,m,o in rows}
 if len(rows)!=2847850: raise AssertionError(('instruction count drift',len(rows)))
 req(by,0x40d918,'mov','esi,DWORD PTR ds:0xc26058')
 req(by,0x40db0c,'mov','DWORD PTR [ebp-0x2c],0x1')
 req(by,0x40db13,'mov','DWORD PTR [ebp-0x28],ebx')
 req(by,0x40db16,'mov','DWORD PTR [ebp-0x24],ebx')
 req(by,0x40db22,'mov','eax,DWORD PTR [esi]')
 req(by,0x40db24,'mov','eax,DWORD PTR [eax+0xe0]')
 req(by,0x40db2a,'push','0xbbf2d4')
 req(by,0x40db2f,'lea','edx,[ebp-0x2c]')
 req(by,0x40db32,'mov','ecx,esi')
 req(by,0x40db34,'call','eax')
 req(by,0x40db36,'mov','BYTE PTR [ebp-0x20],0x1')
 req(by,0x40db3a,'mov','eax,DWORD PTR [esi]')
 req(by,0x40db3c,'mov','eax,DWORD PTR [eax+0xe0]')
 req(by,0x40db42,'push','0xbbf2d0')
 req(by,0x40db47,'lea','edx,[ebp-0x2c]')
 req(by,0x40db4a,'mov','ecx,esi')
 req(by,0x40db4c,'call','eax')
 req(by,0x45ec69,'mov','edi,DWORD PTR ds:0xc26058')
 req(by,0x45ec8c,'mov','eax,DWORD PTR [edi]')
 req(by,0x45ec8e,'mov','edx,DWORD PTR ds:0xbbf2d0')
 req(by,0x45ec94,'mov','eax,DWORD PTR [eax+0xec]')
 req(by,0x45ec9a,'push','0x0'); req(by,0x45ec9c,'push','0x0'); req(by,0x45ec9e,'lea','ecx,[esi+0xcb0]'); req(by,0x45eca4,'push','ecx'); req(by,0x45eca5,'mov','ecx,edi'); req(by,0x45eca7,'call','eax'); req(by,0x45eca9,'mov','DWORD PTR [esi+0xd98],eax')
 req(by,0x45ecaf,'mov','eax,DWORD PTR [edi]')
 req(by,0x45ecb1,'mov','edx,DWORD PTR ds:0xbbf2d4')
 req(by,0x45ecb7,'mov','eax,DWORD PTR [eax+0xec]')
 req(by,0x45ecbd,'push','0x0'); req(by,0x45ecbf,'push','0x0'); req(by,0x45ecc1,'lea','ecx,[esi+0xcb0]'); req(by,0x45ecc7,'push','ecx'); req(by,0x45ecc8,'mov','ecx,edi'); req(by,0x45ecca,'call','eax'); req(by,0x45ecd3,'mov','DWORD PTR [esi+0xd94],eax')
 refs={0xbbf2d0:[],0xbbf2d4:[]}
 for a,m,o in rows:
  for k in refs:
   if f'{k:x}' in o.lower(): refs[k].append(a)
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'singleton':'DAT_00c26058','registration_vtable_slot':'0xe0','lookup_vtable_slot':'0xec','registered_handle_storage':['0x00bbf2d4','0x00bbf2d0']},'inventory':{'decoded_instruction_count':len(rows),'registration_function_entry':'0x0040d910','registration_receiver_load':'0x0040d918','descriptor_initial_dword':1,'descriptor_zero_dwords':2,'descriptor_flag_mutation_between_registrations':{'site':'0x0040db36','offset':'0x0c','value':1},'registrations':[{'handle_storage':'0x00bbf2d4','slot_load':'0x0040db24','call':'0x0040db34'},{'handle_storage':'0x00bbf2d0','slot_load':'0x0040db3c','call':'0x0040db4c'}],'consumer_function_entry':'0x0045ec60','consumer_receiver_load':'0x0045ec69','lookups':[{'handle_storage':'0x00bbf2d0','slot_load':'0x0045ec94','call':'0x0045eca7','result_store':'0x0045eca9','result_field_offset':'0x0d98'},{'handle_storage':'0x00bbf2d4','slot_load':'0x0045ecb7','call':'0x0045ecca','result_store':'0x0045ecd3','result_field_offset':'0x0d94'}],'same_singleton_registers_and_consumes_handles':True,'handle_reference_counts':{f'0x{k:08x}':len(v) for k,v in refs.items()}},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_d94_vtable_key_contract_subset_complete':True,'writable_callback_pair_d94_runtime_value_is_registered_singleton_key_lookup':True,'writable_callback_pair_d94_vtable_ec_concrete_target_proven':False,'writable_callback_pair_d94_value_range_proven':False,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['The proof establishes registration/lookup provenance and ABI identity only; it does not resolve the concrete runtime vtable target at +0xec.','The returned integer domain remains unbounded in this subset.','DAT_00c26058 is runtime storage outside the file-backed .data extent, so a static initial vtable pointer is not available from the image bytes alone.'],'next_step':'Resolve construction/vtable installation for DAT_00c26058 or otherwise bound the +0xec return for handle storage 0x00bbf2d4.'}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe',type=Path); ap.add_argument('upstream',type=Path); ap.add_argument('-o','--output',type=Path); a=ap.parse_args(); r=analyze(a.exe,a.upstream); s=json.dumps(r,indent=2,sort_keys=True)+'\n'; a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__': main()
