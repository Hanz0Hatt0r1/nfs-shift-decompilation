#!/usr/bin/env python3
"""Bound direct source-level storage of exact entry roots in proven slot3 carriers."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3DirectExactRootStorageSource/1"
SOURCE_SHA256="512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
CARRIERS={
 "FUN_00758b50":("void __fastcall FUN_00758b50(int param_1)","param_1"),
 "FUN_00755950":("void __thiscall FUN_00755950(int param_1,undefined4 param_2,double param_3,double param_4)","param_1"),
 "FUN_00770e80":("void __thiscall FUN_00770e80(void *this,undefined8 param_1,undefined8 param_2,char param_3)","this"),
 "FUN_00755a60":("void __thiscall FUN_00755a60(int param_1,undefined4 param_2,double param_3)","param_1"),
 "FUN_00752fc0":("void __fastcall FUN_00752fc0(int param_1)","param_1"),
 "FUN_00760b50":("void __thiscall FUN_00760b50(void *this,double param_1,int param_2)","this"),
 "FUN_00763570":("void __thiscall FUN_00763570(void *this,double param_1)","this"),
 "FUN_00755f80":("float10 __fastcall FUN_00755f80(int param_1)","param_1"),
 "FUN_0076d100":("void __thiscall FUN_0076d100(void *this,char param_1)","this"),
 "FUN_00758810":("void __fastcall FUN_00758810(int param_1)","param_1"),
 "FUN_00769ef0":("void __fastcall FUN_00769ef0(void *param_1)","param_1"),
 "FUN_007675f0":("void __thiscall FUN_007675f0(void *this,void *param_1,undefined4 param_2,float param_3)","this"),
 "FUN_007682c0":("void __thiscall FUN_007682c0(void *this,float param_1,float param_2)","this"),
 "FUN_00766510":("void __fastcall FUN_00766510(void *param_1)","param_1"),
 "FUN_00758fc0":("void __thiscall FUN_00758fc0(void *this,char *param_1,double *param_2)","this"),
}
EXPECTED_ASSIGNMENTS=[
 {"function":"FUN_00758b50","root":"param_1","lhs":"local_2c","text":"local_2c = param_1;","storage":"stack-local"},
 {"function":"FUN_00763570","root":"this","lhs":"local_4c","text":"local_4c = this;","storage":"stack-local"},
]

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def extract(text:str,signature:str)->str:
 s=text.find(signature)
 if s<0:raise ValueError(f'missing carrier signature: {signature}')
 tail=text[s+len(signature):]
 m=re.search(r'\n\n[^\n;]*\bFUN_[0-9a-fA-F]+\([^\n]*\)\s*\n\n\{',tail)
 return text[s:] if m is None else text[s:s+len(signature)+m.start()]

def analyze(source:Path)->dict:
 digest=sha256(source)
 if digest!=SOURCE_SHA256:raise ValueError(f'unexpected SHIFT.exe.c SHA-256: {digest}')
 text=source.read_text(encoding='utf-8',errors='replace')
 found=[]
 for function,(signature,root) in CARRIERS.items():
  body=extract(text,signature)
  pattern=re.compile(r'^\s*([^=]+?)=\s*(?:\([^;=()]+\)\s*)*'+re.escape(root)+r'\s*;\s*$')
  for line in body.splitlines():
   m=pattern.match(line)
   if not m:continue
   lhs=m.group(1).strip()
   storage='stack-local' if lhs.startswith('local_') else 'nonlocal-or-unknown'
   found.append({'function':function,'root':root,'lhs':lhs,'text':line.strip(),'storage':storage})
 if found!=EXPECTED_ASSIGNMENTS:raise ValueError(f'direct exact-root assignment surface drift: {found!r}')
 persistent=[row for row in found if row['storage']!='stack-local']
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1D / P1.3D',
  'authority':{'platform':'PC retail 1.02','retail_decompiler_source_sha256':digest,'source_is_navigation_crosscheck':True},
  'carrier_set':{'count':len(CARRIERS),'semantic_identity_source':'merged P1D exact-root/exact-wheel machine contracts'},
  'direct_exact_root_assignments':{'count':len(found),'rows':found,'persistent_or_unknown_count':len(persistent),'persistent_or_unknown_rows':persistent},
  'adjudication':{
   'source_direct_exact_entry_root_assignment_subset_complete':True,
   'source_direct_exact_entry_root_persistent_store_found':False,
   'derived_alias_storage_ruled_out':False,
   'machine_register_alias_storage_ruled_out':False,
   'stored_or_escaped_aliases_ruled_out':False,
   'callbacks_registered_outside_carriers_ruled_out':False,
   'slot3_writer_provenance_proven':False,
   'p1_3d_complete':False,
   'p1_3_control_producer_complete':False,
   'external_provider_count':7,
  },
  'limits':[
   'This is a source-level exact entry-root assignment subset, not a machine-level universal pointer-escape proof.',
   'It does not follow local aliases after assignment, derived wheel/base pointers, register-only aliases, bulk stores, or callee-created escapes.',
   'Object identity remains owned by the merged retail machine contracts; the pinned source export is used only to bound this direct assignment syntax.'
  ],
  'next_step':'Trace the two stack-local root aliases through their later uses and inventory derived selected-wheel aliases before testing persistent stores or callback registration.'
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
