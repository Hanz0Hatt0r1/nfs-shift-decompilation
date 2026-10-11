#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94HelperInitializer/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94LiteralProducerInventory/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s): return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace'); assert p.stdout; out=[]
 for line in p.stdout:
  m=I.match(line)
  if m: out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 err=p.stderr.read() if p.stderr else ''
 if p.wait(): raise RuntimeError(err)
 return out
def require(by,a,m,o):
 if by.get(a)!=(m,o): raise AssertionError((hex(a),by.get(a),(m,o)))
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA: raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_d94_literal_producer_inventory_subset_complete'):
  raise AssertionError('upstream incomplete')
 rows=dis(exe); by={a:(m,o) for a,m,o in rows}
 if len(rows)!=2847850: raise AssertionError(('instruction count drift',len(rows)))
 require(by,0x872247,'lea','ecx,[esi+0xd94]'); require(by,0x87224d,'lea','edx,[ebp-0x20]'); require(by,0x872257,'call','0x41a560')
 require(by,0x41a566,'mov','esi,ecx'); require(by,0x41a571,'mov','BYTE PTR [ebp-0x4],0x0')
 require(by,0x41a575,'mov','eax,DWORD PTR [ebp-0x4]'); require(by,0x41a578,'push','eax'); require(by,0x41a579,'push','0x0')
 require(by,0x41a57b,'push','0x1'); require(by,0x41a57d,'push','0x1f'); require(by,0x41a57f,'push','0x4'); require(by,0x41a581,'push','0x4'); require(by,0x41a583,'push','0x0')
 require(by,0x41a585,'xor','edx,edx'); require(by,0x41a587,'call','0x62ffd0')
 require(by,0x62ffdf,'mov','esi,ecx'); require(by,0x62ffe5,'mov','ecx,DWORD PTR [ebp+0xc]'); require(by,0x62ffea,'mov','eax,DWORD PTR [ebp+0x8]'); require(by,0x62ffed,'push','ecx'); require(by,0x62ffee,'push','eax')
 require(by,0x62ffef,'mov','ecx,esi'); require(by,0x62fff1,'call','0x62fde0')
 require(by,0x62fdfd,'mov','ebx,DWORD PTR [ebp+0x14]'); require(by,0x62fe03,'and','edi,0x1f'); require(by,0x62fe1f,'mov','ecx,DWORD PTR [ebp+0xc]')
 require(by,0x62fe93,'mov','edx,ebx'); require(by,0x62fe95,'and','edx,0x1f'); require(by,0x62fe9e,'or','edx,0x40'); require(by,0x62fea3,'or','edx,0x800')
 require(by,0x62fecc,'push','ecx'); require(by,0x62fecd,'mov','ecx,esi'); require(by,0x62fecf,'call','0x62f520')
 require(by,0x62f52d,'and','eax,0x1f'); require(by,0x62f530,'cmp','eax,0x1f'); require(by,0x62f536,'jmp','0x457f31')
 require(by,0x457f31,'mov','DWORD PTR [esi+0x14],0x0'); require(by,0x457f38,'jmp','0x62f53d'); require(by,0x62f53d,'je','0x62f5d9')
 require(by,0x62f5d9,'test','edx,0x100'); require(by,0x62f5df,'mov','eax,DWORD PTR [ebp+0x8]'); require(by,0x62f5e2,'mov','DWORD PTR [esi],eax'); require(by,0x62f5e4,'je','0x62f5f2')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},
  'scope':{'field_displacement':'0x0d94','helper_call_site':'0x00872257','helper_target':'0x0041a560','method':'exact fixed-argument propagation through the direct helper chain'},
  'proof':{'decoded_instruction_count':len(rows),'direct_helper_chain':['0x0041a560','0x0062ffd0','0x0062fde0','0x0062f520'],'field_object_register':'esi','forwarded_initializer_arg1':4,'forced_low_flag_bits':'0x1f','base_dword_write_site':'0x0062f5e2','base_dword_written_value':4,'cross_section_trampoline':'0x00457f31'},
  'adjudication':{
   'p13a_fun005ffc50_writable_callback_pair_d94_helper_initializer_subset_complete':True,
   'writable_callback_pair_d94_helper_base_dword_value_proven':True,
   'writable_callback_pair_d94_helper_base_dword_value':4,
   'writable_callback_pair_d94_helper_is_unbounded_value_source':False,
   'writable_callback_pair_d94_runtime_vtable_producer_value_range_proven':False,
   'writable_callback_pair_d94_value_range_proven':False,
   'writable_callback_pair_target_compatible_frontier_empty':False,
   'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,
   'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['This proves only the concrete helper path reached from 0x00872257; it is not a global alias/write closure for +0xd94.','The independent write at 0x0045ecd3 still receives the runtime result of the vtable +0xec call and remains unbounded in this subset.'],
  'next_step':'Resolve the vtable +0xec target/value contract feeding 0x0045ecd3; the helper-mediated +0xd94 initializer no longer contributes an unconstrained value.'}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('exe',type=Path); ap.add_argument('upstream',type=Path); ap.add_argument('-o','--output',type=Path); a=ap.parse_args(); r=analyze(a.exe,a.upstream); s=json.dumps(r,indent=2,sort_keys=True)+'\n'; a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__': main()
