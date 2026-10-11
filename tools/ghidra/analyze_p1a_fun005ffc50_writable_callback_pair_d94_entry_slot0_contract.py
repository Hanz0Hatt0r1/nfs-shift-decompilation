#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94EntrySlot0Contract/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94ConcreteVtable/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s): return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],text=True,capture_output=True,check=True)
 out={}
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m: out[int(m.group(1),16)]=(m.group(2).lower(),norm(m.group(3)))
 return out
def req(by,a,m,o):
 if by.get(a)!=(m,o): raise AssertionError((hex(a),by.get(a),(m,o)))
def vtable_slot0(exe):
 p=subprocess.run(['objdump','-s','--start-address=0xb17fe0','--stop-address=0xb17fe4',str(exe)],text=True,capture_output=True,check=True)
 if 'b17fe0 90528300' not in p.stdout: raise AssertionError('entry vtable slot0 drift')
 return 0x00835290
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA: raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_d94_concrete_vtable_subset_complete'): raise AssertionError('upstream incomplete')
 by=dis(exe)
 if len(by)!=2847850: raise AssertionError(('instruction count drift',len(by)))
 req(by,0x8313e8,'push','0x68'); req(by,0x8313fa,'call','0x8309f0'); req(by,0x830a01,'mov','DWORD PTR [esi],0xb17fe0')
 slot0=vtable_slot0(exe)
 req(by,0x82da79,'mov','eax,DWORD PTR [eax]'); req(by,0x82da83,'call','eax'); req(by,0x82da89,'xor','eax,eax')
 req(by,0x45ecbd,'push','0x0'); req(by,0x45ecbf,'push','0x0'); req(by,0x45ecc1,'lea','ecx,[esi+0xcb0]'); req(by,0x45ecca,'call','eax'); req(by,0x45ecd3,'mov','DWORD PTR [esi+0xd94],eax')
 req(by,0x835298,'lea','ecx,[edi+0x40]'); req(by,0x83529d,'call','0x62f6f0'); req(by,0x8352a4,'test','esi,esi'); req(by,0x8352c7,'call','0x8339e0'); req(by,0x8352d1,'mov','eax,esi'); req(by,0x8352e4,'xor','eax,eax')
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'proof':{'decoded_instruction_count':len(by),'entry_allocation_size':'0x68','entry_constructor':'0x008309f0','entry_vtable':'0x00b17fe0','entry_vtable_slot0_target':f'0x{slot0:08x}','lookup_target':'0x0082da60','consumer_call_site':'0x0045ecca','consumer_destination':'[esi+0xd94]','consumer_entry_arg':'&[esi+0xcb0]','consumer_stack_args':[0,0],'slot0_embedded_container':'this+0x40','slot0_container_acquire':'0x0062f6f0','slot0_finalize':'0x008339e0','slot0_zero_return_possible':True,'slot0_nonzero_return_is_container_derived':True},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_d94_entry_slot0_contract_subset_complete':True,'writable_callback_pair_d94_entry_slot0_concrete_target_proven':True,'writable_callback_pair_d94_entry_slot0_target':'0x00835290','writable_callback_pair_d94_entry_slot0_zero_return_possible':True,'writable_callback_pair_d94_entry_slot0_nonzero_return_domain_bounded':False,'writable_callback_pair_d94_value_range_proven':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This resolves the registered entry class and concrete slot-0 implementation only.','The non-zero return from 0x00835290 is derived from the embedded container at entry+0x40 via 0x0062f6f0 and remains unbounded in this subset.','Therefore +0xd94 must not yet be treated as a proven small integer count solely from the consumer loop shape.'],'next_step':'Trace the return value of 0x0062f6f0/0x0062f460 for the entry+0x40 container and determine whether 0x00835290 returns an index/count, pointer-like token, or another bounded domain before promoting the +0xd94 range gate.'}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe',type=Path); ap.add_argument('upstream',type=Path); ap.add_argument('-o','--output',type=Path); a=ap.parse_args(); r=analyze(a.exe,a.upstream); s=json.dumps(r,indent=2,sort_keys=True)+'\n'; a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__': main()
