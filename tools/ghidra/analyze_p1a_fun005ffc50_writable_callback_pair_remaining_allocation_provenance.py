#!/usr/bin/env python3
"""Classify the four remaining modulo-4/8 callback-alias sites by concrete allocation provenance."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairRemainingAllocationProvenance/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairMod1ZeroGuardExclusion/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
SITES=['0x007a6e9e','0x007a6ea5','0x007f25a0','0x0080b696']
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')

def norm(s:str)->str:return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe:Path):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace'); assert p.stdout
 out=[]
 for line in p.stdout:
  m=I.match(line)
  if m: out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 err=p.stderr.read() if p.stderr else ''
 if p.wait(): raise RuntimeError(err)
 return out

def require(by,a,mn,ops):
 got=by.get(a)
 if got!=(mn,ops): raise AssertionError((hex(a),got,(mn,ops)))

def prove(rows):
 by={a:(m,o) for a,m,o in rows}
 # 0x7a6e9e / 0x7a6ea5: ESI is the return from allocator 0x8868d0 for EDI*8 bytes;
 # EBX is a local zero-based record index.
 for a,m,o in [
  (0x7a6d0a,'xor','ebx,ebx'),(0x7a6df9,'mov','eax,edi'),(0x7a6dfb,'mov','edx,0x8'),
  (0x7a6e00,'mul','edx'),(0x7a6e0a,'call','0x8868d0'),(0x7a6e0f,'mov','esi,eax'),
  (0x7a6e9e,'mov','DWORD PTR [esi+ebx*8+0x4],eax'),(0x7a6ea5,'mov','DWORD PTR [esi+ebx*8],eax'),
  (0x7a6eab,'add','ebx,0x1')]: require(by,a,m,o)
 # 0x7f25a0: EBX is the return from allocator 0x8868d0 for count*4 bytes;
 # EDI is reset to zero immediately before the final consumer loop.
 for a,m,o in [
  (0x7f23b8,'mov','eax,DWORD PTR [ebp+0x8]'),(0x7f23bd,'mov','edx,0x4'),(0x7f23c2,'mul','edx'),
  (0x7f23cc,'call','0x8868d0'),(0x7f23d9,'mov','ebx,eax'),(0x7f2592,'xor','edi,edi'),
  (0x7f25a0,'mov','ecx,DWORD PTR [ebx+edi*4]'),(0x7f25a8,'add','edi,0x1'),
  (0x7f25ab,'cmp','edi,DWORD PTR [ebp+0x8]')]: require(by,a,m,o)
 # 0x80b696: allocator 0x8868c0 returns a header+payload block; EDX is payload base EAX+4,
 # or zero on allocation failure. EAX is a zero-based element index at the copy loop.
 for a,m,o in [
  (0x80b634,'mov','edi,DWORD PTR [esi]'),(0x80b636,'add','edi,DWORD PTR [ebp+0x8]'),
  (0x80b63b,'mov','eax,edi'),(0x80b63d,'mov','edx,0x8'),(0x80b642,'mul','edx'),
  (0x80b64d,'add','ecx,0x4'),(0x80b658,'call','0x8868c0'),(0x80b669,'lea','edx,[eax+0x4]'),
  (0x80b687,'mov','edx,ebx'),(0x80b689,'xor','eax,eax'),
  (0x80b696,'mov','DWORD PTR [edx+eax*8],ecx'),(0x80b69f,'add','eax,0x1'),
  (0x80b6a2,'cmp','eax,DWORD PTR [esi]')]: require(by,a,m,o)
 return [
  {'sites':['0x007a6e9e','0x007a6ea5'],'base_register':'esi','base_provenance':'return value of allocator call 0x008868d0','allocation_size_expression':'edi*8','index_register':'ebx','index_origin':'xor ebx,ebx at 0x007a6d0a','index_step':'add ebx,1 at 0x007a6eab','address_forms':['esi+ebx*8+0x4','esi+ebx*8'],'callback_target_possible':'unresolved_without_allocator_range_proof'},
  {'sites':['0x007f25a0'],'base_register':'ebx','base_provenance':'return value of allocator call 0x008868d0','allocation_size_expression':'[ebp+8]*4','index_register':'edi','index_origin':'xor edi,edi at 0x007f2592','index_bound':'edi < [ebp+8]','address_forms':['ebx+edi*4'],'callback_target_possible':'unresolved_without_allocator_range_proof'},
  {'sites':['0x0080b696'],'base_register':'edx','base_provenance':'payload base alloc_return+4 from 0x008868c0, or zero on allocation failure','allocation_size_expression':'(old_count+requested_count)*8+4','index_register':'eax','index_origin':'xor eax,eax at 0x0080b689','index_bound':'eax < [esi]','address_forms':['edx+eax*8'],'callback_target_possible':'unresolved_without_allocator_range_proof'},
 ]

def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA: raise ValueError(('unexpected executable sha256',sha))
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up.get('adjudication',{}).get('p13a_fun005ffc50_writable_callback_pair_mod1_zero_guard_exclusion_subset_complete'):
  raise AssertionError('upstream incomplete')
 expected=['0x00503328','0x0050334b','0x007a6e9e','0x007a6ea5','0x007f25a0','0x0080b696']
 if up.get('inventory',{}).get('remaining_target_compatible_sites')!=expected: raise AssertionError('frontier drift')
 rows=dis(exe)
 if len(rows)!=2847850: raise AssertionError(('instruction count drift',len(rows)))
 groups=prove(rows)
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},
  'scope':{'classification':'concrete local base/index provenance for the four remaining modulo-4/8 target-compatible sites','targets':['0x00b87b7c','0x00b87b80']},
  'inventory':{'decoded_instruction_count':len(rows),'classified_site_count':4,'classified_sites':SITES,'allocation_provenance_group_count':len(groups),'allocation_provenance_groups':groups,'remaining_modulus1_sites':['0x00503328','0x0050334b']},
  'adjudication':{
   'p13a_fun005ffc50_writable_callback_pair_remaining_allocation_provenance_subset_complete':True,
   'writable_callback_pair_remaining_mod4_mod8_sites_all_allocation_backed':True,
   'writable_callback_pair_allocator_range_disjoint_from_image_proven':False,
   'writable_callback_pair_target_compatible_frontier_empty':False,
   'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,
   'register_loaded_or_aliased_writable_slots_ruled_out':False,
   'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':[
   'This classifies provenance only; allocator returns are not assumed disjoint from the PE image without a separate allocator/address-space proof.',
   'The two modulus-1 sites at 0x00503328/0x0050334b still depend on runtime count/object provenance.',
   'Missing-secondary/runtime aliases and aggregate callback/P1.3 gates remain fail-closed.'
  ],
  'next_step':'Prove allocator/image-range disjointness for 0x008868c0/0x008868d0 or capture authoritative runtime allocation ranges; independently trace [ecx+0xd94] feeding ESI at 0x00503328/0x0050334b.'
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('-o','--output',type=Path);a=ap.parse_args();r=analyze(a.exe,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__': main()
