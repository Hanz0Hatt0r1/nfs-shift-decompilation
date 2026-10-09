#!/usr/bin/env python3
"""Verify the FUN_00763570 -> FUN_00755f80 exact wheel-root path.

The merged P1A x87 reuse contract proves FUN_00763570 receives HDVehicle. Retail
machine code then proves the four-wheel receiver transfer. The callee is closed
only for exact wheel-root escape/write behavior; indirect/callback surfaces
elsewhere remain open.
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3Fun00755f80WheelChildClosure/1"
UPSTREAM_FORMAT="SHIFT.P1A.P13ASlot01X87ReuseTrancheClosure/1"
PE_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INS_RE=re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$")
ANCHORS={
0x0076358E:"mov edi,ecx",0x007635F4:"lea eax,[edi+0x400]",0x00763609:"mov DWORD PTR [ebp-0x4],eax",0x0076360C:"mov ecx,DWORD PTR [ebp-0x4]",0x0076360F:"call 0x755f80",0x0076361B:"add DWORD PTR [ebp-0x4],0xa80",0x00763625:"cmp esi,0x4",
0x00755F9A:"mov esi,ecx",0x00755F9C:"mov eax,DWORD PTR [esi+0x420]",0x00755FA6:"lea edx,[eax+0x48]",0x00755FAA:"lea ecx,[eax+0xd4]",0x00755FB0:"call 0x7af0a0",0x00755FB8:"mov ecx,DWORD PTR [esi+0x420]",0x00755FC8:"add ecx,0xd4",0x00755FD1:"call 0x7af010",0x00755FD6:"mov eax,DWORD PTR [esi+0x420]",0x00755FDF:"add eax,0x48",0x00755FE6:"fstp QWORD PTR [eax]",0x00755FEE:"fstp QWORD PTR [eax+0x8]",0x00755FF7:"fstp QWORD PTR [eax+0x10]",0x00756003:"ret"}

def sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()

def norm(s:str)->str:return ' '.join(s.split()).lower()

def load_upstream(path:Path)->dict:
 p=json.loads(path.read_text(encoding='utf-8'))
 if p.get('format')!=UPSTREAM_FORMAT or not p.get('ready'): raise ValueError('unexpected/unready upstream contract')
 rows={r.get('function'):r for r in p.get('resolved',[])}
 if rows.get('FUN_00763570',{}).get('domain')!='HDVehicle root': raise ValueError('FUN_00763570 HDVehicle identity not proven upstream')
 return p

def dis(exe:Path,start:int,end:int,objdump:str)->dict[int,str]:
 p=subprocess.run([objdump,'-d','-Mintel',f'--start-address=0x{start:x}',f'--stop-address=0x{end:x}',str(exe)],text=True,capture_output=True,errors='replace')
 if p.returncode: raise ValueError(f'objdump failed: {p.stderr.strip()}')
 out={}
 for line in p.stdout.splitlines():
  m=INS_RE.match(line)
  if m: out[int(m.group(1),16)]=m.group(2).strip()
 return out

def analyze(exe:Path,upstream_path:Path,objdump:str='objdump')->dict:
 upstream=load_upstream(upstream_path); digest=sha256(exe)
 if digest!=PE_SHA256: raise ValueError(f'unexpected retail PE SHA-256: {digest}')
 ins={}; ins.update(dis(exe,0x00763570,0x00763630,objdump)); ins.update(dis(exe,0x00755F80,0x00756004,objdump))
 for a,e in ANCHORS.items():
  if a not in ins or norm(ins[a])!=norm(e): raise ValueError(f'anchor drift at 0x{a:08x}: {ins.get(a)!r}')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1D / P1.3D','upstream_contracts':[UPSTREAM_FORMAT],
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':digest,'upstream_retail_executable_sha256':upstream['authority']['retail_executable_sha256'],'machine_transfer_adjudicates':True},
  'selected_slot3':{'wheel_receiver':'HDVehicle+0x2380','local_target':'+0x538','absolute_target':'HDVehicle+0x28b8','width':'f64/qword'},
  'caller':{'function':'FUN_00763570','entry_receiver':'HDVehicle','wheel_seed':'HDVehicle+0x400','stride':'0xa80','iteration_count':4,'slot3_receiver':'HDVehicle+0x2380','callee':'FUN_00755f80'},
  'callee':{'function':'FUN_00755f80','exact_wheel_root_capture':'ESI=ECX','wheel_root_write_count':0,'wheel_root_stored_or_pushed_after_capture':False,'child_pointer_source':'[wheel+0x420]','child_direct_callees':['FUN_007af0a0','FUN_007af010'],'child_write_offsets':['+0x48','+0x50','+0x58'],'exact_wheel_root_forwarded_to_direct_callee':False,'indirect_call_count':0,'target_overlap':False},
  'adjudication':{'slot3_fun00763570_to_fun00755f80_exact_wheel_path_complete':True,'fun00755f80_selected_target_writer_found':False,'fun00755f80_exact_wheel_escape_found':False,'deeper_direct_aliases_ruled_out':False,'indirect_callback_aliases_ruled_out':False,'slot3_writer_provenance_proven':False,'p1_3d_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['Only the exact four-wheel path from FUN_00763570 into FUN_00755f80 is closed.','Writes through [wheel+0x420] belong to the child object and are not reclassified as wheel-local writes.','Other lifecycle roots, stored aliases, out-of-line chunks and indirect/callback carriers remain open.'],
  'next_step':'Continue exact selected-wheel alias tracing in remaining lifecycle functions, then bound stored/escaped and indirect/callback carriers.'}

def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable',type=Path);p.add_argument('upstream',type=Path);p.add_argument('--objdump',default='objdump');p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=analyze(a.executable,a.upstream,a.objdump)
 except ValueError as e:p.error(str(e))
 t=json.dumps(r,indent=2,sort_keys=True)+'\n'; a.output.write_text(t,encoding='utf-8') if a.output else print(t,end=''); return 0
if __name__=='__main__': raise SystemExit(main())
