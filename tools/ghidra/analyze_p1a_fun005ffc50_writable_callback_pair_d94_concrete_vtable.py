#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94ConcreteVtable/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94VtableKeyContract/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout;out=[]
 for line in p.stdout:
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 err=p.stderr.read() if p.stderr else ''
 if p.wait():raise RuntimeError(err)
 return out
def req(by,a,m,o):
 if by.get(a)!=(m,o):raise AssertionError((hex(a),by.get(a),(m,o)))
def read_ptr(exe,va):
 data=exe.read_bytes(); rdata_va=0xaa6000; rdata_off=0x6a4a00
 return struct.unpack_from('<I',data,rdata_off+(va-rdata_va))[0]
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_d94_vtable_key_contract_subset_complete'):raise AssertionError('upstream incomplete')
 rows=dis(exe);by={a:(m,o) for a,m,o in rows}
 if len(rows)!=2847850:raise AssertionError(('instruction count drift',len(rows)))
 req(by,0x823cf0,'push','0x3970');req(by,0x823cfc,'call','0x8868c0');req(by,0x823d0a,'call','0x8323d0');req(by,0x823d1a,'mov','ds:0xc26058,eax');req(by,0x823d50,'mov','DWORD PTR ds:0xc26058,0x0')
 req(by,0x8323d9,'call','0x823d90');req(by,0x8323eb,'mov','DWORD PTR [esi],0xb18d38')
 vt=0xb18d38; reg=read_ptr(exe,vt+0xe0); lookup=read_ptr(exe,vt+0xec)
 if reg!=0x8313b0 or lookup!=0x82da60:raise AssertionError((hex(reg),hex(lookup)))
 req(by,0x8313b8,'mov','eax,DWORD PTR [edi+0x1ac4]');req(by,0x8313c6,'mov','ecx,DWORD PTR [edi+0x1ac8]');req(by,0x831410,'mov','DWORD PTR [edx],esi')
 req(by,0x82da63,'mov','eax,DWORD PTR [ecx+0x1ac8]');req(by,0x82da69,'cmp','DWORD PTR [eax+edx*4],0x0');req(by,0x82da71,'mov','ecx,DWORD PTR [ecx+edx*4]');req(by,0x82da77,'mov','eax,DWORD PTR [ecx]');req(by,0x82da79,'mov','eax,DWORD PTR [eax]');req(by,0x82da83,'call','eax');req(by,0x82da89,'xor','eax,eax')
 writes=[a for a,m,o in rows if 'c26058' in o.lower() and (o.startswith('ds:0xc26058,') or o.startswith('DWORD PTR ds:0xc26058,'))]
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'proof':{'decoded_instruction_count':len(rows),'singleton_allocation_size':'0x3970','singleton_constructor':'0x008323d0','singleton_store':'0x00823d1a','singleton_clear':'0x00823d50','direct_singleton_write_sites':[f'0x{a:08x}' for a in writes],'concrete_vtable':'0x00b18d38','registration_slot_e0_target':f'0x{reg:08x}','lookup_slot_ec_target':f'0x{lookup:08x}','registration_target_writes_handle_index':True,'lookup_target_dispatch_table_offset':'0x1ac8','lookup_target_null_entry_returns_zero':True,'lookup_target_nonnull_entry_dispatches_entry_vtable_slot0':True},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_d94_concrete_vtable_subset_complete':True,'writable_callback_pair_d94_vtable_ec_concrete_target_proven':True,'writable_callback_pair_d94_vtable_ec_target':'0x0082da60','writable_callback_pair_d94_value_range_proven':False,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['Concrete singleton construction and +0xec dispatch target are proven, but non-null handle entries delegate to the registered entry object vtable slot 0.','The return domain of those entry implementations is not yet globally bounded.'],'next_step':'Classify the concrete entry objects constructed by 0x008309f0 and their slot-0 implementations for the 0x00bbf2d4 registration.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('-o','--output',type=Path);a=ap.parse_args();r=analyze(a.exe,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
