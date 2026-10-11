#!/usr/bin/env python3
"""Bound stack-local FNSTENV/FLDENV sequences relevant to FUN_005ffc50 PIC entry."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun005ffc50FnstenvStackRestore/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50CallNextPic/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TEXT_VA,TEXT_RAW=0x00401000,0x00000400
TARGET=0x005ffc50
RANGES={
 'stack_env_A':(0x00913760,0x00913778,'ea4f5c6c31838c0870199482d9737a9144cb251b51efff293beffb4577892fe7'),
 'stack_env_B':(0x00913a18,0x00913a30,'ea4f5c6c31838c0870199482d9737a9144cb251b51efff293beffb4577892fe7'),
 'unowned_decode_A':(0x004177e3,0x00417810,'75b8e4d2e3ff6de4d1868821c32f69251ef3e3e6ac11051e12d1c50c1f7eb270'),
 'unowned_decode_B':(0x0050d058,0x0050d070,'5c7394388b81b8f5203f762ed16b831c4133cf0ea36c1af42bae8ba058534952'),
}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out

def scan_fnstenv(rows):
 return [{'site':f'0x{a:08x}','mnemonic':m,'operand':o} for a,m,o in rows if m in {'fnstenv','fstenv'}]

def exact_stack_windows(rows):
 M={a:(m,o) for a,m,o in rows}
 starts=[0x00913760,0x00913a18]
 out=[]
 expected=[
  (0x0,'sub','esp,0x1c'),(0x3,'fnstenv','[esp]'),(0x6,'and','DWORD PTR [esp+0x4],0xbcff'),
  (0xe,'or','DWORD PTR [esp+0x4],eax'),(0x12,'fldenv','[esp]'),(0x15,'add','esp,0x1c')]
 for s in starts:
  row=[]
  for off,m,o in expected:
   got=M.get(s+off)
   if got!=(m,o):raise AssertionError((hex(s+off),got,(m,o)))
   row.append(f'0x{s+off:08x} {m} {o}')
  out.append({'start':f'0x{s:08x}','end_exclusive':f'0x{s+0x18:08x}','instructions':row})
 return out

def analyze(exe:Path,upstream:Path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up.get('adjudication',{}).get('p13a_fun005ffc50_call_next_pop_pic_subset_complete'):
  raise AssertionError('upstream call-next subset incomplete')
 rows=dis(exe);env=scan_fnstenv(rows)
 expected_env=[
  {'site':'0x004177e4','mnemonic':'fnstenv','operand':'[edi+0x41]'},
  {'site':'0x0050d063','mnemonic':'fnstenv','operand':'[ebx-0x33333334]'},
  {'site':'0x00913763','mnemonic':'fnstenv','operand':'[esp]'},
  {'site':'0x00913a1b','mnemonic':'fnstenv','operand':'[esp]'},
 ]
 if env!=expected_env:raise AssertionError(('fnstenv surface drift',env))
 windows=exact_stack_windows(rows)
 auth={}
 for n,(s,e,h) in RANGES.items():
  raw=blob[TEXT_RAW+s-TEXT_VA:TEXT_RAW+e-TEXT_VA];got=hashlib.sha256(raw).hexdigest()
  if len(raw)!=e-s or got!=h:raise AssertionError(('range drift',n,len(raw),got))
  auth[n]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':got}
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM,'machine_ranges':auth},
  'fnstenv_inventory':{'decoded_instruction_count':len(rows),'total_fnstenv_or_fstenv_count':len(env),'rows':env,
    'stack_esp_fnstenv_count':sum(1 for x in env if x['operand']=='[esp]'),'non_stack_fnstenv_count':sum(1 for x in env if x['operand']!='[esp]')},
  'stack_restore_sequences':windows,
  'stack_restore_semantics':{
    'saved_environment_size_bytes':28,
    'only_memory_mutation_between_save_and_restore':'DWORD PTR [esp+0x4] via AND/OR',
    'gpr_load_from_saved_environment_between_fnstenv_and_fldenv':False,
    'saved_environment_restored_with_fldenv':True,
    'stack_storage_released_immediately_after_restore':True,
    'fun005ffc50_pointer_extracted':False,
  },
  'adjudication':{
    'p13a_fun005ffc50_fnstenv_stack_restore_subset_complete':True,
    'stack_fnstenv_fun005ffc50_reconstruction_found':False,
    'stack_fnstenv_fun005ffc50_indirect_entry_found':False,
    'non_stack_fnstenv_decodes_ruled_out_as_entry':False,
    'other_pic_or_fnstenv_entry_ruled_out':False,
    'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
    'encoded_or_reconstructed_callback_entry_ruled_out':False,
    'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,
    'callbacks_and_indirect_entry_ruled_out':False,
    'fun0067b660_callback_argument_provenance_complete':False,
    'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
    'stored_or_escaped_aliases_ruled_out':False,
    'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
    'This closes only the two exact fnstenv [esp] / fldenv [esp] stack-local sequences present in the retail image.',
    'Neither sequence loads any saved environment field into a GPR before fldenv restores it; only DWORD PTR [esp+4] is masked/ORed as part of environment control-state modification.',
    'The other two objdump FNSTENV decodes use non-stack operands and remain outside this narrow closure; no claim of reachability or non-reachability is made for them.',
    'Other PIC, inter-block dataflow, writable-memory callback slots, return-value provenance, encoded/split values and runtime-generated pointers remain open.',
    'No global reconstructed-entry, callback, slot0, slot1, stored-alias, runtime selected-wheel-store-negative or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Trace writable-memory/runtime callback slots and inter-block/return-value entry to FUN_005ffc50; the two exact stack-local FNSTENV restore sequences no longer need to be treated as EIP-extraction candidates.'
 }
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
