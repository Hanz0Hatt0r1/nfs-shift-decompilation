#!/usr/bin/env python3
"""Close the second exact incoming-caller tranche for HDVehicle+0x4330 carriers."""
from __future__ import annotations
import argparse, hashlib, json, sqlite3, struct
from pathlib import Path

FORMAT="SHIFT.P1B.HDVehicle4330ExternalCallerTranche2/1"
RETAIL_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SQLITE_SHA256="ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED={"SHIFT.GhidraSQLiteIndex/1","SHIFT.GhidraSQLiteIndex/2"}
EXPECTED_FUNCS={
 "0x0074da70":("FUN_0074da70",294,"89cd96cdcee43e2b2cac4f2f90db51a24164189c5dfedc19698f3f84b890b878"),
 "0x00795d60":("FUN_00795d60",8797,"c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14"),
 "0x00798df0":("FUN_00798df0",1581,"88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16"),
}
WINDOWS=[
 (0x0074DACB,"8b036a0005801f000051b90037c100a3b433c100e86c040200","FUN_0074da70 loads literal HDVehicle root into ECX before FUN_0076df50"),
 (0x007990A5,"8b5508d9c052def2518bced9c9d95df0d945f0d996580800008945f0db45f08d8574dcffff50defad9c9d99e5c080000d99ec0000000dd05400bc100d95df0d945f0dd9ec8000000e8","FUN_00798df0 passes stack local EBP-0x238c as FUN_00795d60 param3"),
 (0x007973D8,"85c08b7508898708130000c745e8000000007c338d8fd8120000894d108b55e883c22c528bcee8ada9fdff","FUN_00795d60 reloads param3 from EBP+8 and forwards it in ECX to FUN_00771db0"),
]

class PEImage:
 def __init__(self,data:bytes):
  self.data=data
  if data[:2]!=b"MZ": raise ValueError("not MZ")
  pe=struct.unpack_from("<I",data,0x3c)[0]
  if data[pe:pe+4]!=b"PE\0\0": raise ValueError("missing PE signature")
  coff=pe+4;nsec=struct.unpack_from("<H",data,coff+2)[0];optsz=struct.unpack_from("<H",data,coff+16)[0];opt=coff+20
  if struct.unpack_from("<H",data,opt)[0]!=0x10b: raise ValueError("expected PE32")
  self.base=struct.unpack_from("<I",data,opt+28)[0];table=opt+optsz;self.sections=[]
  for i in range(nsec):
   off=table+i*40;vs,va,rs,rp=struct.unpack_from("<IIII",data,off+8);self.sections.append((va,max(vs,rs),rp))
 def bytes_at_va(self,va:int,size:int)->bytes:
  rva=va-self.base
  for start,span,raw in self.sections:
   if start<=rva<start+span:
    off=raw+(rva-start);return self.data[off:off+size]
  raise ValueError(f"VA not mapped: 0x{va:08x}")

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
 return h.hexdigest()

def all_calls(db):
 return [json.loads(x[0]) for x in db.execute("SELECT raw_json FROM calls")]

def norm(rows):
 return sorted((str(r.get("from_function") or "").lower(),str(r.get("instruction") or "").lower(),str(r.get("to") or "").lower()) for r in rows)

def direct_in(calls,target):
 return [r for r in calls if r.get("indirect") is not True and str(r.get("to") or "").lower()==target]

def direct_out(calls,source,target):
 return [r for r in calls if r.get("indirect") is not True and str(r.get("from_function") or "").lower()==source and str(r.get("to") or "").lower()==target]

def analyze(exe:Path,database:Path)->dict:
 eh,dh=sha256(exe),sha256(database)
 if eh!=RETAIL_SHA256: raise ValueError(f"unexpected retail hash: {eh}")
 if dh!=SQLITE_SHA256: raise ValueError(f"unexpected sqlite hash: {dh}")
 image=PEImage(exe.read_bytes())
 for va,hextext,meaning in WINDOWS:
  actual=image.bytes_at_va(va,len(bytes.fromhex(hextext))).hex()
  if actual!=hextext: raise ValueError(f"retail drift at 0x{va:08x}: {meaning}")
 db=sqlite3.connect(database)
 try:
  row=db.execute("SELECT value FROM metadata WHERE key='format'").fetchone();fmt=None if row is None else row[0]
  if fmt not in SUPPORTED: raise ValueError(f"unsupported sqlite format: {fmt!r}")
  for addr,(name,size,digest) in EXPECTED_FUNCS.items():
   row=db.execute("SELECT name,raw_json FROM functions WHERE lower(address)=?",(addr,)).fetchone()
   if row is None: raise ValueError(f"missing {addr}")
   raw=json.loads(row[1])
   if row[0]!=name or int(raw.get("size") or -1)!=size or raw.get("mnemonic_sha256")!=digest:
    raise ValueError(f"function drift: {addr}")
  calls=all_calls(db)
  if norm(direct_out(calls,"0x0074da70","0x0076df50")) != [("0x0074da70","0x0074dadf","0x0076df50")]:
   raise ValueError("FUN_0074da70 target surface drift")
  if norm(direct_out(calls,"0x00795d60","0x00771db0")) != [("0x00795d60","0x007973fe","0x00771db0")]:
   raise ValueError("FUN_00795d60 target surface drift")
  if norm(direct_in(calls,"0x00795d60")) != [("0x00798df0","0x007990ed","0x00795d60")]:
   raise ValueError("FUN_00795d60 incoming surface drift")
 finally: db.close()
 return {
  "format":FORMAT,"version":1,"ready":True,"owner":"Process 1B / P1.3B",
  "authority":{"platform":"PC retail 1.02","retail_executable_sha256":eh,"ghidra_sqlite_sha256":dh,
               "retail_machine_transfer_adjudicates":True,"sqlite_role":"direct-call inventory/fingerprint cross-check only"},
  "upstream_contracts":["SHIFT.P1B.HDVehicle4330ExternalCallerTranche1/1","SHIFT.HDVehicle64e8Large4330ConsumerPersistenceClosure/1"],
  "fun_0074da70":{"site":"0x0074dadf -> FUN_0076df50","actual_receiver":"literal ECX=0x00c13700 HDVehicle root",
                  "preexisting_hdvehicle_4330_alias_forwarded":False,
                  "classification":"exact-root entry to an already-proven root carrier, not a pre-existing +0x4330 alias"},
  "fun_00795d60":{"site":"0x007973fe -> FUN_00771db0","target_exact_4330_parameter":"ECX",
                  "source_parameter":"FUN_00795d60 param3 loaded from [EBP+8]",
                  "only_direct_caller":"0x007990ed in FUN_00798df0",
                  "caller_param3_argument":"LEA EAX,[EBP-0x238c]; PUSH EAX",
                  "actual_receiver":"stack local EBP-0x238c",
                  "preexisting_hdvehicle_4330_alias_forwarded":False},
  "adjudication":{
   "external_caller_tranche2_complete":True,
   "cumulative_resolved_external_caller_count":4,
   "cumulative_resolved_external_callsite_count":8,
   "remaining_external_caller_count":3,
   "remaining_external_callers":["FUN_00aa2850","Unwind@00a7063f","Unwind@00a72322"],
   "tranche2_preexisting_4330_alias_found":False,
   "external_receiver_provenance_complete":False,
   "indirect_entry_into_carriers_ruled_out":False,
   "global_runtime_derived_4330_alias_surface_complete":False,
   "manager_374_join_to_hdvehicle_4330_complete":False,
   "last_literal_0x004b86cf_rejected":False,
   "p1_3_control_producer_complete":False,
   "external_provider_count":7,
  },
  "limits":[
   "This closes only FUN_0074da70 and FUN_00795d60 from the seven-caller direct frontier.",
   "Three tiny callers remain, including two Ghidra Unwind@ funclets that require enclosing-frame provenance rather than name-based rejection.",
   "Indirect entry and runtime-generated/copied pointer paths remain open."
  ],
  "next_step":"Close FUN_00aa2850 and establish enclosing-frame provenance for Unwind@00a7063f / Unwind@00a72322; then promote direct external receiver provenance only if all three close."
 }

def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("exe",type=Path);p.add_argument("database",type=Path);p.add_argument("--output",type=Path);a=p.parse_args()
 try:r=analyze(a.exe,a.database)
 except ValueError as e:p.error(str(e))
 t=json.dumps(r,indent=2,sort_keys=True)+"\n"
 if a.output:a.output.write_text(t,encoding="utf-8")
 else:print(t,end="")
 return 0
if __name__=="__main__": raise SystemExit(main())
