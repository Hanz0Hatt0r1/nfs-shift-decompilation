#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94LiteralProducerInventory/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairRemainingAllocationProvenance/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
EXPECTED=[0x44ad39,0x45b288,0x45b2ae,0x45ecd3,0x45f43f,0x460ad3,0x464a33,0x464d23,0x466e5d,0x5032ea,0x50337a,0x872247]
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout;out=[]
 for line in p.stdout:
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 err=p.stderr.read() if p.stderr else ''
 if p.wait():raise RuntimeError(err)
 return out
def require(by,a,m,o):
 if by.get(a)!=(m,o):raise AssertionError((hex(a),by.get(a),(m,o)))
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_remaining_allocation_provenance_subset_complete'):raise AssertionError('upstream incomplete')
 rows=dis(exe);by={a:(m,o) for a,m,o in rows}
 if len(rows)!=2847850:raise AssertionError(('instruction count drift',len(rows)))
 hits=[(a,m,o) for a,m,o in rows if '+0xd94]' in o]
 if [a for a,_,_ in hits]!=EXPECTED:raise AssertionError(('literal +d94 surface drift',[hex(a) for a,_,_ in hits]))
 require(by,0x45b28e,'xor','ebx,ebx');require(by,0x45b2ae,'mov','DWORD PTR [esi+0xd94],ebx')
 require(by,0x45ecaf,'mov','eax,DWORD PTR [edi]');require(by,0x45ecb7,'mov','eax,DWORD PTR [eax+0xec]');require(by,0x45ecca,'call','eax');require(by,0x45ecd3,'mov','DWORD PTR [esi+0xd94],eax')
 require(by,0x45f43f,'mov','DWORD PTR [esi+0xd94],ebx')
 require(by,0x872247,'lea','ecx,[esi+0xd94]');require(by,0x872257,'call','0x41a560')
 reads=[a for a,m,o in hits if a not in (0x45b2ae,0x45ecd3,0x45f43f,0x872247)]
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'field_displacement':'0x0d94','method':'whole-image literal displacement inventory plus local producer classification'},'inventory':{'decoded_instruction_count':len(rows),'literal_reference_count':len(hits),'literal_reference_sites':[f'0x{a:08x}' for a,_,_ in hits],'read_or_compare_count':len(reads),'read_or_compare_sites':[f'0x{a:08x}' for a in reads],'direct_write_count':3,'direct_write_sites':['0x0045b2ae','0x0045ecd3','0x0045f43f'],'address_taken_count':1,'address_taken_sites':['0x00872247'],'direct_zero_write_count':2,'direct_zero_write_sites':['0x0045b2ae','0x0045f43f'],'direct_runtime_value_write_count':1,'direct_runtime_value_write_sites':['0x0045ecd3'],'runtime_value_source':{'write_site':'0x0045ecd3','value_register':'eax','source':'return value from indirect virtual call through [edi vtable + 0xec] at 0x0045ecca'},'escaped_address_helper':{'lea_site':'0x00872247','helper_call_site':'0x00872257','helper_target':'0x0041a560'},'remaining_modulus1_sites':['0x00503328','0x0050334b']},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_d94_literal_producer_inventory_subset_complete':True,'writable_callback_pair_d94_literal_surface_has_runtime_or_helper_producers':True,'writable_callback_pair_d94_value_range_proven':False,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['Literal +0xd94 references are complete for the decoded image, but receiver identity and aliases through copied/materialized field addresses are not globally closed.','The write at 0x0045ecd3 receives an unconstrained runtime return value in this subset.','The address of +0xd94 escapes to helper 0x0041a560 at 0x00872257; helper semantics/value bounds remain open.'],'next_step':'Resolve the value contract of the vtable+0xec producer feeding 0x0045ecd3 and the helper 0x0041a560 path from 0x00872257 before attempting a bound for [ecx+0xd94].'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('-o','--output',type=Path);a=ap.parse_args();r=analyze(a.exe,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
