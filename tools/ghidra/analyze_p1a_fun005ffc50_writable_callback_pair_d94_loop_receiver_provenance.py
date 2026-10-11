#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94LoopReceiverProvenance/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94EntryPayloadAddress/1'
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
 raw=exe.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_d94_entry_payload_address_subset_complete'):raise AssertionError('upstream incomplete')
 by=dis(exe)
 if len(by)!=2847850:raise AssertionError(('instruction count drift',len(by)))
 # Loop-owner class and its source/derived containers.
 req(by,0x503589,'mov','DWORD PTR [esi],0xac4a58');req(by,0x503594,'lea','ecx,[esi+0x38]')
 req(by,0x5035b8,'push','0x0');req(by,0x5035ba,'push','0x1f');req(by,0x5035bc,'push','0x4');req(by,0x5035be,'mov','edx,0x4');req(by,0x5035c5,'call','0x502e20')
 req(by,0x4d748b,'push','0xd98');req(by,0x4d7491,'call','0x62ffd0');req(by,0x62f5e2,'mov','DWORD PTR [esi],eax')
 # Derived +0x38 record copies source-record DWORD 0 without reinterpretation.
 req(by,0x5033e6,'add','esi,0x4');req(by,0x5033ec,'call','0x546290');req(by,0x5033f1,'mov','eax,DWORD PTR [eax]')
 req(by,0x502fe2,'mov','DWORD PTR [ecx],eax');req(by,0x50341d,'add','ecx,0x38');req(by,0x503423,'call','0x5030d0')
 # Loop consumes DWORD 0 of that derived record as the +0xd94 receiver.
 req(by,0x50325a,'lea','ecx,[ebx+0x38]');req(by,0x50325d,'call','0x546290');req(by,0x503262,'mov','edi,eax')
 req(by,0x5032e6,'mov','ecx,DWORD PTR [edi]');req(by,0x5032ea,'cmp','DWORD PTR [ecx+0xd94],esi');req(by,0x50337a,'cmp','esi,DWORD PTR [ecx+0xd94]')
 # FUN_005031e0 has one literal pointer in the retail image; it is vtable slot 1 at 0x00ac4a5c.
 if raw.count((0x5031e0).to_bytes(4,'little'))!=1:raise AssertionError('FUN_005031e0 pointer multiplicity drift')
 sec=subprocess.run(['objdump','-s','--start-address=0xac4a58','--stop-address=0xac4a60',str(exe)],text=True,capture_output=True,check=True).stdout
 if 'ac4a58 f0355000 e0315000' not in sec:raise AssertionError('loop-owner vtable drift')
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'proof':{'decoded_instruction_count':len(by),'loop_function':'0x005031e0','loop_owner_vtable':'0x00ac4a58','loop_owner_vtable_slot1':'0x005031e0','loop_function_pointer_occurrences_in_image':1,'source_container':'loop_owner+0x4','source_container_element_stride':'0x0d98','derived_container':'loop_owner+0x38','derived_record_first_dword_source':'source_record+0x0','loop_receiver_expression':'DWORD PTR [derived_record+0x0]','loop_receiver_load_site':'0x005032e6','loop_bound_sites':['0x005032ea','0x0050337a'],'runtime_writer_receiver_expression':'ECX/ESI of FUN_0045ec60','runtime_writer_site':'0x0045ecd3'},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_d94_loop_receiver_provenance_subset_complete':True,'writable_callback_pair_d94_loop_receiver_source_chain_proven':True,'writable_callback_pair_d94_writer_consumer_receiver_identity_proven':False,'writable_callback_pair_d94_runtime_writer_relevant_to_loop_bound_proven':False,'writable_callback_pair_d94_value_range_proven':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This proves the complete local receiver chain used by the two +0xd94 loop comparisons, not the provenance of source_record+0x0 before it enters loop_owner+0x4.','The runtime writer at 0x0045ecd3 uses the ECX receiver of FUN_0045ec60; no equality with the loop receiver is established here.','Identical displacement +0xd94 is not receiver identity.'],'next_step':'Classify producers of source_record+0x0 in loop_owner+0x4 and compare their object class/provenance with the FUN_0045ec60 receiver; only then decide whether 0x0045ecd3 belongs to the loop-bound producer frontier.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('-o','--output',type=Path);a=ap.parse_args();r=analyze(a.exe,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
