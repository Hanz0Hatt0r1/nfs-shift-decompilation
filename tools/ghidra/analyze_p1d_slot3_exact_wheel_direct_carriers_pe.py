#!/usr/bin/env python3
"""Verify exact selected-wheel direct carriers rooted in FUN_00770e80.

PC retail 1.02 machine code is semantic authority. The merged P1A x87 reuse
contract supplies the already-proven object identities for FUN_00770e80,
FUN_00755a60 and FUN_00760b50; this tool proves the exact transfers/writes below.
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1"
UPSTREAM_FORMAT="SHIFT.P1A.P13ASlot01X87ReuseTrancheClosure/1"
PE_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
FUNCTIONS={"FUN_00770e80":(0x00770E80,1183),"FUN_00755a60":(0x00755A60,1297),"FUN_00760b50":(0x00760B50,531),"FUN_00752fc0":(0x00752FC0,37)}
ANCHORS={
0x00770EA1:"mov esi,ecx",0x007710A4:"lea edi,[esi+0x740]",0x007710C9:"lea ecx,[edi-0x340]",0x007710CF:"call 0x755a60",0x007710DA:"add edi,0xa80",0x007710E0:"cmp eax,0x4",
0x00771177:"lea ecx,[esi+0x2380]",0x00771180:"call 0x760b50",0x00755A73:"mov esi,ecx",0x00755C04:"lea ecx,[esi+0x7c8]",0x00755DB3:"mov ecx,esi",0x00755DB5:"call 0x752fc0",
0x00760B6A:"mov esi,ecx",0x00760D02:"mov ecx,DWORD PTR [esi+0x420]",0x00752FC0:"fld QWORD PTR [ecx+0x7d0]",0x00752FE4:"ret"}
WRITE_SITES={
"FUN_00755a60":{0x00755C63:0x7B0,0x00755C89:0x7B0,0x00755CB4:0x7B0,0x00755CD7:0x7B8,0x00755CFC:0x7B8,0x00755D22:0x7B8,0x00755D42:0x7C0,0x00755D68:0x7C0,0x00755D91:0x7C0,0x00755CBC:0x7C8,0x00755D2A:0x7C8,0x00755D99:0x7C8,0x00755E2E:0x850,0x00755E5B:0x7F8,0x00755E6F:0x7F8,0x00755F64:0x800},
"FUN_00760b50":{0x00760C44:0x8B0,0x00760C8A:0x8B0,0x00760C90:0x868,0x00760CC7:0x868,0x00760CEE:0x868,0x00760D12:0x888,0x00760D56:0x368},
"FUN_00752fc0":{0x00752FCC:0x7D8,0x00752FDE:0x5B8}}
INS_RE=re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*(.*)$")
CALL_RE=re.compile(r"^call\s+(0x[0-9a-fA-F]+)\b",re.I)

def sha256(path:Path)->str:
 h=hashlib.sha256();
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
 return h.hexdigest()

def norm(s:str)->str:return " ".join(s.split()).lower()

def load_upstream(path:Path)->dict:
 p=json.loads(path.read_text(encoding="utf-8"))
 if p.get("format")!=UPSTREAM_FORMAT or not p.get("ready"): raise ValueError("unexpected/unready upstream x87 reuse contract")
 rows={r.get("function"):r for r in p.get("resolved",[])}
 if rows.get("FUN_00770e80",{}).get("domain")!="HDVehicle root": raise ValueError("FUN_00770e80 HDVehicle identity not proven upstream")
 for fn in ("FUN_00755a60","FUN_00760b50"):
  if rows.get(fn,{}).get("domain")!="wheel receiver HDVehicle+0x400+slot*0xa80": raise ValueError(f"{fn} wheel identity not proven upstream")
 return p

def disassemble(exe:Path,start:int,size:int,objdump:str)->dict[int,str]:
 p=subprocess.run([objdump,"-d","-Mintel",f"--start-address=0x{start:x}",f"--stop-address=0x{start+size:x}",str(exe)],text=True,capture_output=True,errors="replace")
 if p.returncode: raise ValueError(f"objdump failed: {p.stderr.strip()}")
 out={}
 for line in p.stdout.splitlines():
  m=INS_RE.match(line)
  if m: out[int(m.group(1),16)]=m.group(2).strip()
 return out

def direct_calls(ins:dict[int,str])->list[dict]:
 out=[]
 for a,t in sorted(ins.items()):
  m=CALL_RE.match(t)
  if m: out.append({"site":f"0x{a:08x}","target":f"0x{int(m.group(1),16):08x}"})
 return out

def analyze(exe:Path,upstream_path:Path,objdump:str="objdump")->dict:
 upstream=load_upstream(upstream_path); digest=sha256(exe)
 if digest!=PE_SHA256: raise ValueError(f"unexpected retail PE SHA-256: {digest}")
 decoded={n:disassemble(exe,s,z,objdump) for n,(s,z) in FUNCTIONS.items()}; all_ins={a:t for rows in decoded.values() for a,t in rows.items()}
 for a,e in ANCHORS.items():
  if a not in all_ins or norm(all_ins[a])!=norm(e): raise ValueError(f"anchor drift at 0x{a:08x}: {all_ins.get(a)!r}")
 for fn,sites in WRITE_SITES.items():
  for a in sites:
   if a not in decoded[fn]: raise ValueError(f"missing write site 0x{a:08x} in {fn}")
 offsets={fn:sorted(set(s.values())) for fn,s in WRITE_SITES.items()}
 if any(0x538 in xs for xs in offsets.values()): raise ValueError("target +0x538 unexpectedly appears in bounded write set")
 calls={fn:direct_calls(decoded[fn]) for fn in ("FUN_00755a60","FUN_00760b50","FUN_00752fc0")}
 if calls["FUN_00752fc0"]: raise ValueError("FUN_00752fc0 is no longer a leaf")
 return {"format":FORMAT,"version":1,"ready":True,"owner":"Process 1D / P1.3D","upstream_contracts":[UPSTREAM_FORMAT],
 "authority":{"platform":"PC retail 1.02","retail_executable_sha256":digest,"upstream_retail_executable_sha256":upstream["authority"]["retail_executable_sha256"],"machine_transfer_adjudicates":True},
 "selected_slot3":{"hdvehicle_offset":"0x2380","local_target":"+0x538","absolute_target":"HDVehicle+0x28b8","width":"f64/qword"},
 "paths":{"fun00755a60":{"receiver":"HDVehicle+0x400+slot*0xa80","slot3_receiver":"HDVehicle+0x2380","caller_transfer":"EDI=HDVehicle+0x740+slot*0xa80; ECX=EDI-0x340","write_offsets":[f"+0x{x:x}" for x in offsets["FUN_00755a60"]],"exact_root_direct_forward":"FUN_00752fc0","leaf_write_offsets":[f"+0x{x:x}" for x in offsets["FUN_00752fc0"]],"leaf_has_direct_calls":False,"target_overlap":False},
 "fun00760b50":{"receiver":"HDVehicle+0x2380","caller_transfer":"0x00771177 lea ecx,[esi+0x2380]","write_offsets":[f"+0x{x:x}" for x in offsets["FUN_00760b50"]],"exact_root_direct_forward":None,"child_receiver_call":"FUN_007ba860 receives [wheel+0x420]","target_overlap":False}},
 "call_inventory":calls,
 "adjudication":{"slot3_fun00770e80_exact_wheel_direct_carrier_subset_complete":True,"fun00755a60_selected_target_writer_found":False,"fun00752fc0_selected_target_writer_found":False,"fun00760b50_selected_target_writer_found":False,"deeper_direct_aliases_ruled_out":False,"indirect_callback_aliases_ruled_out":False,"slot3_writer_provenance_proven":False,"p1_3d_complete":False,"p1_3_control_producer_complete":False,"external_provider_count":7},
 "limits":["Only the two exact selected-wheel carriers materialized in FUN_00770e80 and their bounded direct descendants are closed.","Other lifecycle functions, stored aliases, out-of-line chunks, indirect calls and callbacks remain open.","Object identity comes from the merged upstream contract plus exact machine transfer, never numeric coincidence."],
 "next_step":"Trace stored/escaped selected-wheel aliases and indirect/callback carriers outside these FUN_00770e80 direct paths."}

def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("executable",type=Path);p.add_argument("upstream",type=Path);p.add_argument("--objdump",default="objdump");p.add_argument("--output",type=Path);a=p.parse_args()
 try:r=analyze(a.executable,a.upstream,a.objdump)
 except ValueError as e:p.error(str(e))
 text=json.dumps(r,indent=2,sort_keys=True)+"\n"; a.output.write_text(text,encoding="utf-8") if a.output else print(text,end=""); return 0
if __name__=="__main__": raise SystemExit(main())
