#!/usr/bin/env python3
"""Close the exact-root and +0x7c8 derived register aliases in FUN_00755a60."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3Fun00755a60RegisterAliasClosure/1"
DIRECT_FORMAT="SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1"
REGISTER_SUBSET_FORMAT="SHIFT.P1D.Slot3RegisterAliasSubsetClosure/1"
PE_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
ROOT_START=0x00755A60
ROOT_SIZE=1297
CLAMP_START=0x00753620
CLAMP_SIZE=41
SAVE_SITE=0x00755A6C
CAPTURE_SITE=0x00755A73
DERIVED_SITE=0x00755C04
DERIVED_CALL_SITE=0x00755DAE
ROOT_FORWARD_SITE=0x00755DB3
ROOT_FORWARD_CALL_SITE=0x00755DB5
RESTORE_SITE=0x00755F6A
EXPECTED_ESI_USE_SITES=[
 0x00755A6C,0x00755A73,0x00755A87,0x00755A94,0x00755A9C,0x00755AA2,0x00755AB0,0x00755AC1,0x00755AD4,0x00755AFC,
 0x00755B02,0x00755B08,0x00755B11,0x00755B24,0x00755B2D,0x00755B48,0x00755B51,0x00755B5A,0x00755B63,0x00755B69,
 0x00755B8F,0x00755BCC,0x00755BFE,0x00755C04,0x00755C0A,0x00755C15,0x00755C1E,0x00755C27,0x00755C30,0x00755C40,
 0x00755C52,0x00755C63,0x00755C6B,0x00755C89,0x00755CAC,0x00755CB4,0x00755CC8,0x00755CD7,0x00755CDF,0x00755CFC,
 0x00755D1A,0x00755D22,0x00755D36,0x00755D42,0x00755D4A,0x00755D68,0x00755D89,0x00755D91,0x00755DB3,0x00755DBA,
 0x00755DC0,0x00755DCB,0x00755DDA,0x00755E02,0x00755E08,0x00755E16,0x00755E2E,0x00755E41,0x00755E51,0x00755E5B,
 0x00755E6F,0x00755EAE,0x00755EFC,0x00755F0B,0x00755F16,0x00755F27,0x00755F2F,0x00755F5E,0x00755F64,0x00755F6A,
]
EXPECTED_ECX_DERIVED_WINDOW=[
 (0x00755C04,"lea ecx,[esi+0x7c8]"),
 (0x00755C39,"fld QWORD PTR [ecx]"),
 (0x00755CBA,"fsubr QWORD PTR [ecx]"),
 (0x00755CBC,"fstp QWORD PTR [ecx]"),
 (0x00755D28,"fsubr QWORD PTR [ecx]"),
 (0x00755D2A,"fstp QWORD PTR [ecx]"),
 (0x00755D97,"fsubr QWORD PTR [ecx]"),
 (0x00755D99,"fstp QWORD PTR [ecx]"),
]
EXPECTED_CLAMP={
 0x00753623:"fld QWORD PTR [ebp+0x8]",
 0x00753626:"fcom QWORD PTR [ecx]",
 0x0075362F:"fstp QWORD PTR [ecx]",
 0x00753637:"fld QWORD PTR [ebp+0x10]",
 0x0075363A:"fcom QWORD PTR [ecx]",
 0x00753641:"jnp 0x75362f",
 0x00753646:"ret 0x10",
}
INS_RE=re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$")
ESI_RE=re.compile(r"\besi\b",re.I)
EXACT_ESI_VALUE_RE=re.compile(r"^(?:mov\s+(?:e(?:ax|bx|cx|dx|di|bp)|DWORD PTR \[[^\]]+\]),esi|push\s+esi)$",re.I)
ECX_RE=re.compile(r"\becx\b",re.I)
CALL_RE=re.compile(r"^call\s+(0x[0-9a-fA-F]+)\b",re.I)


def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()


def norm(s:str)->str:return " ".join(s.split()).lower()


def load_direct(path:Path)->dict:
 p=json.loads(path.read_text(encoding='utf-8'))
 if p.get('format')!=DIRECT_FORMAT or not p.get('ready'):raise ValueError('unexpected/unready direct-carrier contract')
 row=p.get('paths',{}).get('fun00755a60',{})
 if row.get('receiver')!='HDVehicle+0x400+slot*0xa80' or row.get('slot3_receiver')!='HDVehicle+0x2380':raise ValueError('FUN_00755a60 receiver proof drift')
 if row.get('exact_root_direct_forward')!='FUN_00752fc0' or row.get('target_overlap') is not False:raise ValueError('FUN_00755a60 direct-carrier proof drift')
 if row.get('leaf_has_direct_calls') is not False:raise ValueError('FUN_00752fc0 leaf proof drift')
 return p


def load_register_subset(path:Path)->dict:
 p=json.loads(path.read_text(encoding='utf-8'))
 if p.get('format')!=REGISTER_SUBSET_FORMAT or not p.get('ready'):raise ValueError('unexpected/unready register-alias subset contract')
 a=p.get('adjudication',{})
 if a.get('machine_proven_register_alias_subset_complete') is not True or a.get('other_register_aliases_ruled_out') is not False:raise ValueError('register-alias frontier drift')
 return p


def disassemble(exe:Path,start:int,size:int,objdump:str)->dict[int,str]:
 p=subprocess.run([objdump,'-d','-Mintel',f'--start-address=0x{start:x}',f'--stop-address=0x{start+size:x}',str(exe)],text=True,capture_output=True,errors='replace')
 if p.returncode:raise ValueError(f'objdump failed: {p.stderr.strip()}')
 out={}
 for line in p.stdout.splitlines():
  m=INS_RE.match(line)
  if m:out[int(m.group(1),16)]=m.group(2).strip()
 return out


def analyze(exe:Path,direct_path:Path,register_subset_path:Path,objdump:str='objdump')->dict:
 direct=load_direct(direct_path);load_register_subset(register_subset_path)
 digest=sha256(exe)
 if digest!=PE_SHA256:raise ValueError(f'unexpected retail PE SHA-256: {digest}')
 root=disassemble(exe,ROOT_START,ROOT_SIZE,objdump);clamp=disassemble(exe,CLAMP_START,CLAMP_SIZE,objdump)
 anchors={SAVE_SITE:'push esi',CAPTURE_SITE:'mov esi,ecx',DERIVED_SITE:'lea ecx,[esi+0x7c8]',DERIVED_CALL_SITE:'call 0x753620',ROOT_FORWARD_SITE:'mov ecx,esi',ROOT_FORWARD_CALL_SITE:'call 0x752fc0',RESTORE_SITE:'pop esi'}
 for a,e in anchors.items():
  if a not in root or norm(root[a])!=norm(e):raise ValueError(f'FUN_00755a60 anchor drift at 0x{a:08x}: {root.get(a)!r}')
 uses=[a for a,t in sorted(root.items()) if ESI_RE.search(t)]
 if uses!=EXPECTED_ESI_USE_SITES:raise ValueError(f'FUN_00755a60 ESI-use surface drift: {[hex(x) for x in uses]!r}')
 exact_value=[]
 for a in uses:
  if a<=CAPTURE_SITE or a>=RESTORE_SITE:continue
  t=norm(root[a])
  if EXACT_ESI_VALUE_RE.match(t):exact_value.append((a,t))
 if exact_value!=[(ROOT_FORWARD_SITE,'mov ecx,esi')]:raise ValueError(f'unexpected exact-root register transfer(s): {exact_value!r}')
 ecx_window=[(a,norm(t)) for a,t in sorted(root.items()) if DERIVED_SITE<=a<ROOT_FORWARD_SITE and ECX_RE.search(t)]
 expected_window=[(a,norm(t)) for a,t in EXPECTED_ECX_DERIVED_WINDOW]
 if ecx_window!=expected_window:raise ValueError(f'wheel+0x7c8 ECX lifetime drift: {ecx_window!r}')
 for a,e in EXPECTED_CLAMP.items():
  if a not in clamp or norm(clamp[a])!=norm(e):raise ValueError(f'FUN_00753620 anchor drift at 0x{a:08x}: {clamp.get(a)!r}')
 clamp_calls=[]
 for a,t in sorted(clamp.items()):
  if CALL_RE.match(t):clamp_calls.append((a,t))
 if clamp_calls:raise ValueError(f'FUN_00753620 unexpectedly calls out: {clamp_calls!r}')
 clamp_ecx=[(a,norm(t)) for a,t in sorted(clamp.items()) if ECX_RE.search(t)]
 expected_clamp_ecx=[(0x00753626,'fcom qword ptr [ecx]'),(0x0075362F,'fstp qword ptr [ecx]'),(0x0075363A,'fcom qword ptr [ecx]')]
 if clamp_ecx!=expected_clamp_ecx:raise ValueError(f'FUN_00753620 ECX surface drift: {clamp_ecx!r}')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1D / P1.3D','upstream_contracts':[DIRECT_FORMAT,REGISTER_SUBSET_FORMAT],
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':digest,'upstream_retail_executable_sha256':direct['authority']['retail_executable_sha256'],'machine_transfer_adjudicates':True},
  'selected_slot3':{'wheel_receiver':'HDVehicle+0x2380','local_target':'+0x538','absolute_target':'HDVehicle+0x28b8..+0x28bf'},
  'fun00755a60':{'root_capture':'0x00755a73 ESI=ECX','esi_use_count':len(uses),'exact_root_value_transfers_after_capture':['0x00755db3 ECX=ESI -> 0x00755db5 FUN_00752fc0'],'unexpected_exact_root_transfer_found':False,'known_exact_root_leaf':'FUN_00752fc0','known_exact_root_leaf_has_direct_calls':False,'derived_subfield_alias':'0x00755c04 ECX=ESI+0x7c8','derived_subfield_alias_persists_to_call':'0x00755dae FUN_00753620'},
  'fun00753620':{'receiver':'selected wheel+0x7c8','write_offsets':['+0x0'],'absolute_selected_wheel_write_offsets':['+0x7c8'],'direct_call_count':0,'selected_target_overlap':False},
  'adjudication':{'fun00755a60_exact_root_register_alias_subset_complete':True,'fun00755a60_unexpected_exact_root_register_escape_found':False,'fun00755a60_wheel_7c8_derived_alias_subset_complete':True,'fun00753620_selected_target_writer_found':False,'machine_register_alias_storage_ruled_out':False,'callee_created_aliases_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'slot3_writer_provenance_proven':False,'p1_3d_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['This closes only the exact ESI root transfer and the one machine-proven wheel+0x7c8 ECX subfield alias in FUN_00755a60.','The exact-root transfer to FUN_00752fc0 is consumed from the merged direct-carrier proof; this tranche does not re-own its leaf semantics.','Other derived subobject aliases, callee-created aliases, aggregate stores, callbacks and indirect carriers remain open.'],
  'next_step':'Inventory callee-created aliases reached from other machine-proven selected-wheel subobjects and then compose the closed FUN_00755950/FUN_00755f80/FUN_00760b50/FUN_00755a60 register paths without promoting the global escape gate prematurely.'
 }


def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable',type=Path);p.add_argument('direct',type=Path);p.add_argument('register_subset',type=Path);p.add_argument('--objdump',default='objdump');p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=analyze(a.executable,a.direct,a.register_subset,a.objdump)
 except ValueError as e:p.error(str(e))
 text=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(text,encoding='utf-8')
 else:print(text,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())
