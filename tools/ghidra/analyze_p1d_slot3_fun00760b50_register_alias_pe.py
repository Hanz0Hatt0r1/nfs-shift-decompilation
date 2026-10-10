#!/usr/bin/env python3
"""Close explicit register/storage escape of the exact selected wheel in FUN_00760b50.

The merged direct-carrier contract supplies selected-wheel identity. This pass
uses exact PC retail machine code only to bound explicit uses of the captured
ESI alias; it does not re-own the upstream receiver proof or child semantics.
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3Fun00760b50RegisterAliasClosure/1"
DIRECT_FORMAT="SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1"
REGISTER_SUBSET_FORMAT="SHIFT.P1D.Slot3RegisterAliasSubsetClosure/1"
PE_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
START=0x00760B50
SIZE=531
SAVE_SITE=0x00760B69
CAPTURE_SITE=0x00760B6A
CHILD_LOAD_SITE=0x00760D02
CHILD_CALL_SITE=0x00760D4B
RESTORE_SITE=0x00760D5C
EXPECTED_ESI_USE_SITES=[
 0x00760B69,0x00760B6A,0x00760B6C,0x00760B78,0x00760B89,
 0x00760BCF,0x00760BD5,0x00760BDF,0x00760BED,0x00760BF3,
 0x00760C0B,0x00760C13,0x00760C19,0x00760C3E,0x00760C44,
 0x00760C4A,0x00760C8A,0x00760C90,0x00760C9E,0x00760CA4,
 0x00760CAC,0x00760CBB,0x00760CC7,0x00760CD1,0x00760CE8,
 0x00760CEE,0x00760CF9,0x00760D02,0x00760D0C,0x00760D12,
 0x00760D18,0x00760D1E,0x00760D24,0x00760D56,0x00760D5C,
]
EXPECTED_CALLS=[
 {"site":"0x00760b98","target":"0x007af0a0"},
 {"site":"0x00760c27","target":"0x00749340"},
 {"site":"0x00760cd7","target":"0x00900b10"},
 {"site":"0x00760d4b","target":"0x007ba860"},
]
ANCHORS={
 SAVE_SITE:"push esi",
 CAPTURE_SITE:"mov esi,ecx",
 CHILD_LOAD_SITE:"mov ecx,DWORD PTR [esi+0x420]",
 CHILD_CALL_SITE:"call 0x7ba860",
 RESTORE_SITE:"pop esi",
}
INS_RE=re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$")
CALL_RE=re.compile(r"^call\s+(0x[0-9a-fA-F]+)\b",re.I)
ESI_RE=re.compile(r"\besi\b",re.I)
ESI_MEM_RE=re.compile(r"\[esi(?:\+0x[0-9a-f]+)?\]",re.I)


def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()


def norm(s:str)->str:return " ".join(s.split()).lower()


def load_direct(path:Path)->dict:
 p=json.loads(path.read_text(encoding="utf-8"))
 if p.get("format")!=DIRECT_FORMAT or not p.get("ready"):
  raise ValueError("unexpected/unready direct-carrier upstream contract")
 slot=p.get("selected_slot3",{})
 if slot.get("hdvehicle_offset")!="0x2380" or slot.get("local_target")!="+0x538":
  raise ValueError("selected slot3 identity drift")
 row=p.get("paths",{}).get("fun00760b50",{})
 if row.get("receiver")!="HDVehicle+0x2380" or row.get("target_overlap") is not False:
  raise ValueError("FUN_00760b50 selected-wheel proof drift")
 if row.get("child_receiver_call")!="FUN_007ba860 receives [wheel+0x420]":
  raise ValueError("FUN_00760b50 child receiver proof drift")
 return p


def load_register_subset(path:Path)->dict:
 p=json.loads(path.read_text(encoding="utf-8"))
 if p.get("format")!=REGISTER_SUBSET_FORMAT or not p.get("ready"):
  raise ValueError("unexpected/unready register-alias subset contract")
 slot=p.get("selected_slot3",{})
 if slot.get("wheel_receiver")!="HDVehicle+0x2380" or slot.get("local_target")!="+0x538":
  raise ValueError("register-alias subset selected slot3 drift")
 a=p.get("adjudication",{})
 if a.get("machine_proven_register_alias_subset_complete") is not True or a.get("other_register_aliases_ruled_out") is not False:
  raise ValueError("register-alias subset frontier drift")
 return p


def disassemble(exe:Path,objdump:str)->dict[int,str]:
 p=subprocess.run([objdump,"-d","-Mintel",f"--start-address=0x{START:x}",f"--stop-address=0x{START+SIZE:x}",str(exe)],text=True,capture_output=True,errors="replace")
 if p.returncode:raise ValueError(f"objdump failed: {p.stderr.strip()}")
 out={}
 for line in p.stdout.splitlines():
  m=INS_RE.match(line)
  if m:out[int(m.group(1),16)]=m.group(2).strip()
 return out


def direct_calls(ins:dict[int,str])->list[dict]:
 out=[]
 for a,t in sorted(ins.items()):
  m=CALL_RE.match(t)
  if m:out.append({"site":f"0x{a:08x}","target":f"0x{int(m.group(1),16):08x}"})
 return out


def analyze(exe:Path,direct_path:Path,register_subset_path:Path,objdump:str="objdump")->dict:
 direct=load_direct(direct_path)
 load_register_subset(register_subset_path)
 digest=sha256(exe)
 if digest!=PE_SHA256:raise ValueError(f"unexpected retail PE SHA-256: {digest}")
 ins=disassemble(exe,objdump)
 if not ins or min(ins)!=START:raise ValueError("FUN_00760b50 disassembly boundary drift")
 for a,e in ANCHORS.items():
  if a not in ins or norm(ins[a])!=norm(e):raise ValueError(f"anchor drift at 0x{a:08x}: {ins.get(a)!r}")
 calls=direct_calls(ins)
 if calls!=EXPECTED_CALLS:raise ValueError(f"FUN_00760b50 call surface drift: {calls!r}")
 uses=[a for a,t in sorted(ins.items()) if ESI_RE.search(t)]
 if uses!=EXPECTED_ESI_USE_SITES:raise ValueError(f"FUN_00760b50 ESI-use surface drift: {[hex(x) for x in uses]!r}")
 post=[]
 invalid=[]
 for a in uses:
  if a<=CAPTURE_SITE or a>=RESTORE_SITE:continue
  t=ins[a]
  row={"site":f"0x{a:08x}","instruction":t}
  post.append(row)
  if not ESI_MEM_RE.search(t):invalid.append(row)
 if invalid:raise ValueError(f"explicit exact-wheel register escape candidate(s): {invalid!r}")
 # The one callee-facing derived pointer is a dereference of wheel+0x420,
 # not a copy of the exact wheel root itself.
 if norm(ins[CHILD_LOAD_SITE])!=norm("mov ecx,DWORD PTR [esi+0x420]") or norm(ins[CHILD_CALL_SITE])!=norm("call 0x7ba860"):
  raise ValueError("selected-wheel child handoff drift")
 return {
  "format":FORMAT,"version":1,"ready":True,"owner":"Process 1D / P1.3D",
  "upstream_contracts":[DIRECT_FORMAT,REGISTER_SUBSET_FORMAT],
  "authority":{"platform":"PC retail 1.02","retail_executable_sha256":digest,"upstream_retail_executable_sha256":direct["authority"]["retail_executable_sha256"],"machine_transfer_adjudicates":True},
  "selected_slot3":{"wheel_receiver":"HDVehicle+0x2380","local_target":"+0x538","absolute_target":"HDVehicle+0x28b8..+0x28bf"},
  "function":{"name":"FUN_00760b50","start":"0x00760b50","size":SIZE,"root_capture":{"site":"0x00760b6a","instruction":"mov esi,ecx","alias":"ESI = exact selected wheel"},"esi_use_count":len(uses),"post_capture_pre_restore_esi_use_count":len(post),"post_capture_pre_restore_esi_uses_are_memory_base_only":True,"explicit_root_value_copy_after_capture_found":False,"explicit_root_push_after_capture_found":False,"explicit_root_nonlocal_store_after_capture_found":False,"explicit_root_forward_to_direct_callee_found":False},
  "child_handoff":{"site":"0x00760d02","source":"[wheel+0x420]","destination_register":"ECX","callee_site":"0x00760d4b","callee":"FUN_007ba860","is_exact_wheel_root":False,"classification":"dereferenced child pointer, not selected-wheel root escape"},
  "call_inventory":calls,
  "adjudication":{"fun00760b50_exact_selected_wheel_register_alias_subset_complete":True,"fun00760b50_exact_selected_wheel_explicit_register_escape_found":False,"fun00760b50_child_pointer_handoff_distinguished":True,"machine_register_alias_storage_ruled_out":False,"callee_created_aliases_ruled_out":False,"stored_or_escaped_aliases_ruled_out":False,"slot3_writer_provenance_proven":False,"p1_3d_complete":False,"p1_3_control_producer_complete":False,"external_provider_count":7},
  "limits":["This closes only explicit post-capture uses of ESI inside FUN_00760b50 for the already-proven selected slot3 receiver.","A child pointer loaded from [wheel+0x420] is a distinct receiver and is not reclassified as an escape of the exact selected-wheel root.","Other exact-wheel register aliases, callee-created aliases, aggregate stores, callbacks and indirect carriers remain open."],
  "next_step":"Continue outside the now-closed FUN_00758b50/FUN_00755950/FUN_00755f80/FUN_00760b50 register paths: bound the non-duplicated residual register surface of FUN_00755a60 and then callee-created selected-wheel aliases; keep FUN_00766510/FUN_00758fc0 ownership with their existing P1D tranche."
 }


def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("executable",type=Path);p.add_argument("direct",type=Path);p.add_argument("register_subset",type=Path);p.add_argument("--objdump",default="objdump");p.add_argument("--output",type=Path);a=p.parse_args()
 try:r=analyze(a.executable,a.direct,a.register_subset,a.objdump)
 except ValueError as e:p.error(str(e))
 text=json.dumps(r,indent=2,sort_keys=True)+"\n"
 if a.output:a.output.write_text(text,encoding="utf-8")
 else:print(text,end="")
 return 0

if __name__=="__main__":raise SystemExit(main())
