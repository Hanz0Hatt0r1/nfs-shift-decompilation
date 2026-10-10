#!/usr/bin/env python3
"""Bound direct machine persistence of stable exact-root carrier registers across the 16-carrier P1D set."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3SixteenCarrierDirectRootPersistence/1"
PE_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INSN_RE=re.compile(r"^\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}\s+)+)\s*([^\s]+)\s*(.*)$")
GPRS={"eax","ebx","ecx","edx","esi","edi","ebp","esp"}

SPECS={
 "FUN_00758b50": {"start":0x00758b50,"size":1136,"instruction_count":323,"machine_sha256":"c2fec71ef5a88d9802f0a176f4f6674f0cb6211d43548a4ec6bf1b45373ba220","root_reg":"edi","intervals":[(0x00758b98,0x00758bce),(0x00758d70,0x00758fb0)]},
 "FUN_00755950": {"start":0x00755950,"size":66,"instruction_count":19,"machine_sha256":"581672ff3f3990ca40d8869725c89966a43c89330786ea800c3517fa02389d29","root_reg":"edx","intervals":[(0x00755956,0x00755992)]},
 "FUN_00770e80": {"start":0x00770e80,"size":1183,"instruction_count":315,"machine_sha256":"eafcd64bdef560bfece1e18ba07349156d5992cacc8ac34bcd88b0e156c3f0b4","root_reg":"esi","intervals":[(0x00770ea1,0x00771315)]},
 "FUN_00755a60": {"start":0x00755a60,"size":1297,"instruction_count":393,"machine_sha256":"7064be6d7afc007796a22dd439105572a63e4a7adb17df7b7a0ca3e216c7a5df","root_reg":"esi","intervals":[(0x00755a73,0x00755f6a)]},
 "FUN_00752fc0": {"start":0x00752fc0,"size":37,"instruction_count":7,"machine_sha256":"830ecb8fa09bf20a07a8e269f4d44351dc167232bba00f5d9a7d931675d111cc","root_reg":"ecx","intervals":[(0x00752fc0,0x00752fe5)]},
 "FUN_00760b50": {"start":0x00760b50,"size":531,"instruction_count":146,"machine_sha256":"6befdb2ebc8df4b449242abcaaeb9a8c9aab00a03dfaa6f2c0a03d7e1087d9a0","root_reg":"esi","intervals":[(0x00760b6a,0x00760d5c)]},
 "FUN_00763570": {"start":0x00763570,"size":3277,"instruction_count":971,"decoded_size":3276,"machine_sha256":"c251e9114cdfe57c63eaf836727da51255e44ba38d8550fcebf5d5849047a470","root_reg":"edi","intervals":[(0x0076358e,0x0076423d)]},
 "FUN_00755f80": {"start":0x00755f80,"size":132,"instruction_count":46,"machine_sha256":"7ca9b230d67c47859cabb8a5f2e6cc6f4cea620765addeca5ec1a9e393c7f0f9","root_reg":"esi","intervals":[(0x00755f9a,0x00755fe5)]},
 "FUN_0076d100": {"start":0x0076d100,"size":508,"instruction_count":142,"machine_sha256":"a52188e2049aca73eeb1c4de13652a3e9a1ba2d113722d0d0c49e00c6db5bd9b","root_reg":"esi","intervals":[(0x0076d118,0x0076d2ec)]},
 "FUN_00758810": {"start":0x00758810,"size":347,"instruction_count":114,"machine_sha256":"1d06be3f816f57d65e9b6e8efb669ed1d20ab2966bc7c418fe52a5d32b47b5f8","root_reg":"edi","intervals":[(0x0075882e,0x00758962)]},
 "FUN_00769ef0": {"start":0x00769ef0,"size":774,"instruction_count":252,"machine_sha256":"882839f3a01e34e923e4b32b3e71d0f5d9c417109df0899769e90a165d114ebb","root_reg":"esi","intervals":[(0x00769f0a,0x0076a1ee)]},
 "FUN_007675f0": {"start":0x007675f0,"size":1340,"instruction_count":436,"machine_sha256":"2255f6e983a08a36f9f3a4ee2f3194d293cfa712a48b546875b0a9bd53e01c74","root_reg":"esi","intervals":[(0x00767610,0x00767b22)]},
 "FUN_007682c0": {"start":0x007682c0,"size":335,"instruction_count":121,"machine_sha256":"7ef6c0cb7fdca913bbc7e4a3128c56f5a69cd4d4b300323bdc1ade0825897acc","root_reg":"esi","intervals":[(0x007682da,0x00768405)]},
 "FUN_00766510": {"start":0x00766510,"size":4310,"instruction_count":1128,"machine_sha256":"f4834c7dd376cf80d87935cbea0da8eb3ff446108983ed5d49190b2cd4c0fc85","root_reg":"esi","intervals":[(0x0076652f,0x007675de)]},
 "FUN_00758fc0": {"start":0x00758fc0,"size":364,"instruction_count":118,"machine_sha256":"b308d2be888da1428340950a0c0c96d9ca09e4b7efedae30962c17a961c475fb","root_reg":"esi","intervals":[(0x00758fe4,0x00759122)]},
 "FUN_00765c40": {"start":0x00765c40,"size":2249,"instruction_count":647,"decoded_size":2248,"machine_sha256":"ecd9a4981e8b62bb1d323d0a195b498ff293b27458d56ffcb451db45f5c3351c","root_reg":"esi","intervals":[(0x00765c5f,0x00766506)]},
}

EXPECTED_STORES=[
 {"function":"FUN_00758b50","address":"0x00758b9b","operands":"dword ptr [ebp-0x1c],edi","storage":"stack-local"},
 {"function":"FUN_00763570","address":"0x00763590","operands":"dword ptr [ebp-0x3c],edi","storage":"stack-local"},
]
EXPECTED_COPY_ADDRESSES=[
"0x00770f6f","0x00770fa7","0x00770fbd","0x00770fd7","0x00771069","0x007712c4",
"0x00755db3","0x0076388a","0x0076d129","0x0076d130","0x0076d137","0x0076d191","0x0076d2bf",
"0x0076a1be","0x0076a1e0","0x007677ad","0x00768369","0x0076839e","0x00766da3","0x00766db8",
"0x00765d08","0x00765da8","0x00765f29",
]

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()

def disassemble(exe:Path,start:int,size:int)->list[dict]:
 p=subprocess.run(["objdump","-d","-Mintel",f"--start-address=0x{start:x}",f"--stop-address=0x{start+size:x}",str(exe)],check=True,capture_output=True,text=True)
 rows=[]
 for line in p.stdout.splitlines():
  m=INSN_RE.match(line)
  if not m:continue
  rows.append({"address":int(m.group(1),16),"bytes":bytes.fromhex(m.group(2)),"mnemonic":m.group(3).lower(),"operands":m.group(4).strip().lower()})
 return rows

def active(addr:int,intervals:list[tuple[int,int]])->bool:
 return any(lo<=addr<hi for lo,hi in intervals)

def analyze(exe:Path)->dict:
 digest=sha256(exe)
 if digest!=PE_SHA256:raise ValueError(f"unexpected retail executable SHA-256: {digest}")
 funcs={}
 stores=[];pushes=[];copies=[]
 for name,spec in SPECS.items():
  rows=disassemble(exe,spec["start"],spec["size"])
  blob=b"".join(r["bytes"] for r in rows)
  body_hash=hashlib.sha256(blob).hexdigest()
  if len(blob)!=spec.get("decoded_size",spec["size"]) or len(rows)!=spec["instruction_count"] or body_hash!=spec["machine_sha256"]:
   raise ValueError(f"{name} machine body drift: bytes={len(blob)} insns={len(rows)} sha={body_hash}")
  reg=spec["root_reg"]
  for row in rows:
   if not active(row["address"],spec["intervals"]):continue
   ops=[x.strip() for x in row["operands"].split(",",1)]
   if row["mnemonic"]=="push" and row["operands"]==reg:
    pushes.append({"function":name,"address":f"0x{row['address']:08x}","operands":row["operands"]})
   if row["mnemonic"]=="mov" and len(ops)==2 and ops[1]==reg:
    if "[" in ops[0]:
     storage="stack-local" if ("[ebp" in ops[0] or "[esp" in ops[0]) else "nonstack-or-unknown"
     stores.append({"function":name,"address":f"0x{row['address']:08x}","operands":row["operands"],"storage":storage})
    elif ops[0] in GPRS:
     copies.append({"function":name,"address":f"0x{row['address']:08x}","destination":ops[0],"operands":row["operands"]})
  funcs[name]={
   "start":f"0x{spec['start']:08x}","ghidra_size":spec["size"],"decoded_byte_count":len(blob),"instruction_count":len(rows),"machine_bytes_sha256":body_hash,
   "stable_exact_root_register":reg,
   "stable_intervals":[{"start":f"0x{lo:08x}","end_exclusive":f"0x{hi:08x}"} for lo,hi in spec["intervals"]],
  }
 if stores!=EXPECTED_STORES:raise ValueError(f"exact-root direct store surface drift: {stores!r}")
 if pushes:raise ValueError(f"unexpected exact-root push surface: {pushes!r}")
 if [x["address"] for x in copies]!=EXPECTED_COPY_ADDRESSES:raise ValueError(f"exact-root register-copy surface drift: {copies!r}")
 if {x["destination"] for x in copies}!={"ecx"}:raise ValueError(f"unexpected widened exact-root GPR alias: {copies!r}")
 return {
  "format":FORMAT,"version":1,"ready":True,"owner":"Process 1D / P1.3D",
  "authority":{"platform":"PC retail 1.02","retail_executable_sha256":digest,"machine_bytes_adjudicate":True},
  "scope":{"carrier_count":len(SPECS),"functions":funcs,
           "stable_exact_root_register_intervals_seeded_from_merged_machine_contracts":True,
           "fun00758b50_stack_bridge":{"store":"0x00758b9b [ebp-0x1c] = EDI exact root","restore":"0x00758d70 EDI = [ebp-0x1c]"}},
  "direct_exact_root_value_surface":{
   "memory_store_count":len(stores),"memory_stores":stores,
   "nonstack_or_unknown_memory_store_count":sum(x["storage"]!="stack-local" for x in stores),
   "push_count":len(pushes),"pushes":pushes,
   "register_copy_count":len(copies),"register_copies":copies,
   "register_copy_destinations":sorted({x["destination"] for x in copies}),
  },
  "adjudication":{
   "machine_direct_exact_root_storage_16_carrier_subset_complete":True,
   "machine_direct_exact_root_nonstack_store_found":False,
   "machine_direct_exact_root_push_found":False,
   "machine_direct_exact_root_new_gpr_alias_beyond_ecx_receiver_reload_found":False,
   "machine_register_alias_storage_ruled_out":False,
   "derived_alias_storage_ruled_out":False,
   "runtime_generated_pointer_stores_ruled_out":False,
   "callee_created_aliases_ruled_out":False,
   "callbacks_registered_outside_carriers_ruled_out":False,
   "stored_or_escaped_aliases_ruled_out":False,
   "slot3_writer_provenance_proven":False,
   "p1_3d_complete":False,"p1_3_control_producer_complete":False,"external_provider_count":7,
  },
  "limits":[
   "This closes direct stores, pushes, and immediate GPR copies whose source operand is a machine-proven stable exact-root carrier register inside the pinned intervals.",
   "ECX receiver reloads remain call/temporary register traffic, not persistence; their callees are separate alias surfaces and are not globally reclassified here.",
   "Derived/interior addresses, aggregate copies, values reconstructed from memory, callbacks, indirect entry, encoded/copied/runtime-generated pointers, and callee-created aliases remain open.",
   "No numeric offset or scalar equality is promoted to selected-wheel identity."
  ],
  "next_step":"Trace derived/interior register aliases and runtime-generated/copied pointer stores outside this direct exact-root value surface; compose callback/indirect-entry evidence before changing the global stored-or-escaped-alias gate."
 }

def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("exe",type=Path);p.add_argument("--output",type=Path);a=p.parse_args()
 try:r=analyze(a.exe)
 except (ValueError,subprocess.CalledProcessError) as e:p.error(str(e))
 text=json.dumps(r,indent=2,sort_keys=True)+"\n"
 if a.output:a.output.write_text(text,encoding="utf-8")
 else:print(text,end="")
 return 0
if __name__=="__main__":raise SystemExit(main())
