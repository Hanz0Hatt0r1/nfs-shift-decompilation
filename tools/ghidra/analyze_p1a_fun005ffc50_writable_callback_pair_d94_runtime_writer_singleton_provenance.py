#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94RuntimeWriterSingletonProvenance/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94LoopReceiverProvenance/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ',',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],text=True,capture_output=True,check=True);out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def req(by,a,m,o):
 if by.get(a)!=(m,o):raise AssertionError((hex(a),by.get(a),(m,o)))
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_d94_loop_receiver_provenance_subset_complete'):raise AssertionError('upstream incomplete')
 rows=dis(exe);by={a:(m,o) for a,m,o in rows}
 if len(rows)!=2847850:raise AssertionError(('instruction count drift',len(rows)))
 req(by,0xd362b9,'push','0x46e0');req(by,0xd362be,'call','0x8868c0');req(by,0xd362d9,'call','0x45ef50');req(by,0xd362ec,'mov','ds:0xbc185c,eax');req(by,0xd362f3,'mov','DWORD PTR ds:0xbc185c,esi')
 req(by,0x45ef59,'mov','esi,ecx');req(by,0x45ef78,'mov','DWORD PTR [esi],0xab5644');req(by,0x45ef7e,'mov','DWORD PTR [esi+0x4],0xab55f0');req(by,0x45ef85,'mov','DWORD PTR [esi+0x8],0xab55e4')
 req(by,0x462d10,'mov','eax,DWORD PTR [ecx+0xd9c]');req(by,0x462d16,'cmp','eax,DWORD PTR [ecx+0xcbc]');req(by,0x462d1e,'jmp','0x45ec60');req(by,0x4694fb,'call','0x462d10')
 refs=[(a,m,o) for a,m,o in rows if '0xbc185c' in o]
 writes=[(a,m,o) for a,m,o in refs if m=='mov' and (o.startswith('ds:0xbc185c,') or o.startswith('DWORD PTR ds:0xbc185c,'))]
 if [a for a,_,_ in writes] != [0xd362ec,0xd362f3]:raise AssertionError(('singleton writer surface drift',[hex(a) for a,_,_ in writes]))
 branches=[(a,m,o) for a,m,o in rows if m in ('call','jmp') and o=='0x45ec60']
 if [(a,m) for a,m,_ in branches] != [(0x462d1e,'jmp')]:raise AssertionError(('writer direct-entry surface drift',[(hex(a),m) for a,m,_ in branches]))
 wrapper_calls=[a for a,m,o in rows if m=='call' and o=='0x462d10']
 if wrapper_calls != [0x4694fb]:raise AssertionError(('wrapper caller surface drift',[hex(a) for a in wrapper_calls]))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'proof':{'decoded_instruction_count':len(rows),'runtime_writer_singleton_storage':'0x00bc185c','singleton_direct_reference_count':len(refs),'singleton_direct_write_count':len(writes),'singleton_direct_write_sites':[f'0x{a:08x}' for a,_,_ in writes],'singleton_allocation_size':'0x46e0','singleton_constructor':'0x0045ef50','constructor_primary_vtable':'0x00ab5644','constructor_secondary_tables':['0x00ab55f0','0x00ab55e4'],'writer_body':'0x0045ec60','writer_guard_wrapper':'0x00462d10','writer_guard_fields':['+0xd9c','+0xcbc'],'writer_body_direct_branch_sites':['0x00462d1e'],'writer_wrapper_direct_call_sites':['0x004694fb'],'writer_d94_store':'0x0045ecd3'},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_d94_runtime_writer_singleton_provenance_subset_complete':True,'writable_callback_pair_d94_runtime_writer_singleton_constructor_proven':True,'writable_callback_pair_d94_runtime_writer_direct_entry_surface_bounded':True,'writable_callback_pair_d94_writer_consumer_receiver_identity_proven':False,'writable_callback_pair_d94_runtime_writer_relevant_to_loop_bound_proven':False,'writable_callback_pair_d94_value_range_proven':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This proves the direct singleton construction/storage and direct branch surface of the runtime writer class; it does not prove that every possible FUN_0045ec60 receiver is the global singleton.','The loop receiver still originates from source_record+0 in loop_owner+0x4; no equality with DAT_00bc185c is established.','Indirect/copy-based propagation of the singleton pointer remains outside this bounded subset.'],'next_step':'Inventory exact/direct propagation of DAT_00bc185c into memory or source-record construction, and independently classify source_record+0 producer paths before deciding writer relevance to the loop bound.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('-o','--output',type=Path);a=ap.parse_args();r=analyze(a.exe,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
