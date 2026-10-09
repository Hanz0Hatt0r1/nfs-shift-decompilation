#!/usr/bin/env python3
"""Close the two exact entry-root stack aliases found in the proven slot3 carrier set."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3StackExactRootAliasClosure/1"
SOURCE_SHA256="512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
FUNCTIONS={
 "FUN_00758b50":"void __fastcall FUN_00758b50(int param_1)",
 "FUN_00763570":"void __thiscall FUN_00763570(void *this,double param_1)",
}
EXPECTED={
 "FUN_00758b50":{
  "alias":"local_2c",
  "lines":[
   "int local_2c;",
   "local_2c = param_1;",
   "FUN_007aefb0((void *)(*(int *)(local_2c + 0x33a0) + 0xd4),pdVar4 + 2,pdVar4 + 5);",
   "pdVar3 = (double *)FUN_00753590(local_90,pdVar4 + 5,*(double **)(local_2c + 0x33a0));",
   "iVar1 = *(int *)(local_2c + 0x33a0);",
   "param_1 = local_2c;",
  ],
 },
 "FUN_00763570":{
  "alias":"local_4c",
  "lines":["void *local_4c;","local_4c = this;"],
 },
}

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def extract(text:str,signature:str)->str:
 s=text.find(signature)
 if s<0:raise ValueError(f'missing signature: {signature}')
 tail=text[s+len(signature):]
 m=re.search(r'\n\n[^\n;]*\bFUN_[0-9a-fA-F]+\([^\n]*\)\s*\n\n\{',tail)
 return text[s:] if m is None else text[s:s+len(signature)+m.start()]

def analyze(source:Path)->dict:
 digest=sha256(source)
 if digest!=SOURCE_SHA256:raise ValueError(f'unexpected SHIFT.exe.c SHA-256: {digest}')
 text=source.read_text(encoding='utf-8',errors='replace')
 observed={}
 for fn,sig in FUNCTIONS.items():
  body=extract(text,sig);alias=EXPECTED[fn]['alias']
  lines=[line.strip() for line in body.splitlines() if alias in line]
  if lines!=EXPECTED[fn]['lines']:raise ValueError(f'{fn} alias-use surface drift: {lines!r}')
  observed[fn]={'alias':alias,'lines':lines}
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1D / P1.3D',
  'authority':{'platform':'PC retail 1.02','retail_decompiler_source_sha256':digest,'source_is_navigation_crosscheck':True},
  'aliases':{
   'FUN_00758b50':{
    'alias':'local_2c','source_root':'param_1 = exact HDVehicle root',
    'uses':['dereference HDVehicle+0x33a0 for chassis BODY transform input','dereference HDVehicle+0x33a0 for vector add input','load HDVehicle+0x33a0','restore local param_1 from local_2c'],
    'passes_exact_root_to_callee':False,'stores_exact_root_nonlocally':False,'escapes_exact_root':False,
   },
   'FUN_00763570':{
    'alias':'local_4c','source_root':'this = exact HDVehicle root','uses_after_assignment':0,
    'passes_exact_root_to_callee':False,'stores_exact_root_nonlocally':False,'escapes_exact_root':False,
   },
  },
  'adjudication':{
   'source_stack_local_exact_entry_root_alias_subset_complete':True,
   'source_stack_local_exact_entry_root_escape_found':False,
   'derived_wheel_alias_storage_ruled_out':False,
   'machine_register_alias_storage_ruled_out':False,
   'stored_or_escaped_aliases_ruled_out':False,
   'slot3_writer_provenance_proven':False,
   'p1_3d_complete':False,
   'p1_3_control_producer_complete':False,
   'external_provider_count':7,
  },
  'limits':[
   'This closes only the two exact entry-root stack aliases found by the preceding direct-assignment source contract.',
   'Dereferencing HDVehicle+0x33a0 yields a distinct chassis BODY pointer and is not an escape of the HDVehicle root itself.',
   'Derived wheel/base pointers, machine register aliases, callee-created aliases, aggregate stores and callbacks remain open.'
  ],
  'next_step':'Inventory derived selected-wheel/base aliases materialized inside the proven carrier set, then test whether any are stored or forwarded beyond already-closed direct callees.'
 }

def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=analyze(a.source)
 except ValueError as e:p.error(str(e))
 t=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(t,encoding='utf-8')
 else:print(t,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())
