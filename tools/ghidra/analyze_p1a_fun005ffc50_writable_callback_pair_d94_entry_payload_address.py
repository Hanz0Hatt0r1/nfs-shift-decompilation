#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94EntryPayloadAddress/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94EntrySlot0Contract/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ',',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],text=True,capture_output=True,check=True);out={}
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out[int(m.group(1),16)]=(m.group(2).lower(),norm(m.group(3)))
 return out
def req(by,a,m,o):
 if by.get(a)!=(m,o):raise AssertionError((hex(a),by.get(a),(m,o)))
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_d94_entry_slot0_contract_subset_complete'):raise AssertionError('upstream incomplete')
 by=dis(exe)
 if len(by)!=2847850:raise AssertionError(('instruction count drift',len(by)))
 req(by,0x830ceb,'push','0x0');req(by,0x830ced,'push','0xb189e8');req(by,0x830cf2,'push','0x4');req(by,0x830cf7,'push','0x80');req(by,0x830cfd,'mov','edx,0x100');req(by,0x830d05,'call','0x62f910')
 req(by,0x62f52d,'and','eax,0x1f');req(by,0x62f54c,'test','edx,0x100');req(by,0x62f5af,'cmp','eax,0x1f');req(by,0x62f600,'mov','DWORD PTR [esi+0x4],ecx');req(by,0x62f603,'mov','DWORD PTR [esi+0x10],edx')
 req(by,0x63ac4c,'mov','DWORD PTR [esi+0x4],edi');req(by,0x63ad09,'imul','eax,DWORD PTR [ebp-0x4]');req(by,0x63ad1f,'add','eax,DWORD PTR [esi+0x4]')
 req(by,0x62f791,'mov','edx,DWORD PTR [esi]');req(by,0x62f795,'call','0x63ac90');req(by,0x62f7a6,'mov','esi,DWORD PTR [esi+0x14]');req(by,0x62f7a9,'add','esi,DWORD PTR [ebp-0x4]');req(by,0x62f7c4,'mov','eax,esi')
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'proof':{'decoded_instruction_count':len(by),'entry_container':'entry+0x40','container_init_call':'0x00830d05','container_init_flags':4,'container_block_quantity_argument':'0x80','container_edx_argument':'0x100','block_payload_base_field':'block+0x4','allocator_slot_formula':'payload_base + index * stride','slot_allocator':'0x0063ac90','slot0_container_acquire':'0x0062f6f0','nonzero_slot0_return_is_payload_address':True},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_d94_entry_payload_address_subset_complete':True,'writable_callback_pair_d94_entry_slot0_nonzero_return_is_payload_address':True,'writable_callback_pair_d94_value_range_proven':False,'writable_callback_pair_d94_writer_consumer_receiver_identity_proven':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['The non-zero slot-0 result is an address into allocator payload, not a proven small integer count.','This does not establish that the writer receiver at 0x0045ecd3 is the same object type/instance as the +0xd94 loop consumers at 0x005032ea and 0x0050337a.','No aggregate gate is promoted.'],'next_step':'Resolve receiver identity/provenance between the 0x0045ecd3 writer and the two +0xd94 loop consumers before treating this runtime producer as relevant to their bound.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('-o','--output',type=Path);a=ap.parse_args();r=analyze(a.exe,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
