#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94LoopSourceKeySemantics/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94LoopReceiverProvenance/1'
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
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_d94_loop_receiver_provenance_subset_complete'):raise AssertionError('upstream incomplete')
 by=dis(exe)
 if len(by)!=2847850:raise AssertionError(('instruction count drift',len(by)))
 # Candidate key from caller-side object; null key falls back to static empty string.
 req(by,0x5033d7,'call','eax');req(by,0x5033d9,'mov','eax,DWORD PTR [eax]');req(by,0x5033db,'test','eax,eax');req(by,0x5033dd,'mov','edi,eax');req(by,0x5033e1,'mov','edi,0xaa9b60')
 # Non-null source_record+0 becomes first comparator argument.
 req(by,0x5033ec,'call','0x546290');req(by,0x5033f1,'mov','eax,DWORD PTR [eax]');req(by,0x5033f3,'test','eax,eax');req(by,0x5033fb,'push','edi');req(by,0x5033fc,'push','eax');req(by,0x5033fd,'call','0x901179')
 # Default comparator path is ASCII case-insensitive and NUL-terminated.
 req(by,0x9011b2,'jmp','0x901071');req(by,0x90107b,'movzx','eax,BYTE PTR [esi]');req(by,0x90107e,'lea','ecx,[eax-0x41]');req(by,0x901082,'cmp','ecx,0x19');req(by,0x901087,'add','eax,0x20');req(by,0x90108a,'movzx','ecx,BYTE PTR [edx]');req(by,0x90108d,'lea','edi,[ecx-0x41]');req(by,0x901091,'cmp','edi,0x19');req(by,0x901096,'add','ecx,0x20');req(by,0x901099,'test','eax,eax');req(by,0x90109d,'cmp','eax,ecx');req(by,0x9010a2,'sub','eax,ecx')
 # Locale-aware branch still receives the same two character-pointer inputs.
 req(by,0x90117f,'cmp','DWORD PTR ds:0xc32218,esi');req(by,0x9011bb,'push','DWORD PTR [ebp+0x8]');req(by,0x9011be,'call','0x9010a6')
 sec=subprocess.run(['objdump','-s','--start-address=0xaa9b60','--stop-address=0xaa9b64',str(exe)],text=True,capture_output=True,check=True).stdout
 if 'aa9b60 00000000' not in sec:raise AssertionError('empty-string fallback drift')
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'proof':{'decoded_instruction_count':len(by),'source_record_key_load_site':'0x005033f1','source_record_key_null_guard_site':'0x005033f3','comparison_call_site':'0x005033fd','comparison_target':'0x00901179','default_ascii_compare_target':'0x00901071','empty_key_fallback':'0x00aa9b60','empty_key_fallback_first_dword':0,'default_compare_ascii_uppercase_range':['0x41','0x5a'],'default_compare_ascii_fold_delta':'0x20','default_compare_terminates_on_nul':True,'locale_aware_compare_target':'0x009010a6','non_null_source_record_dword0_is_string_key_input':True},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_d94_loop_source_key_semantics_subset_complete':True,'writable_callback_pair_d94_loop_source_record_dword0_string_key_compatible':True,'writable_callback_pair_d94_loop_source_record_dword0_unique_type_proven':False,'writable_callback_pair_d94_writer_consumer_receiver_identity_proven':False,'writable_callback_pair_d94_runtime_writer_relevant_to_loop_bound_proven':False,'writable_callback_pair_d94_value_range_proven':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This proves usage semantics for non-null source_record+0 values selected by FUN_00503390; it does not prove a unique C++ type or constructor for those values.','String-key-compatible usage does not by itself prove inequality with the runtime writer singleton.','Producer/copy paths for source_record+0 remain open.'],'next_step':'Classify the producer/copy surface for source_record+0 and combine it with the bounded DAT_00bc185c propagation frontier before deciding writer/loop receiver identity.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('-o','--output',type=Path);a=ap.parse_args();r=analyze(a.exe,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
