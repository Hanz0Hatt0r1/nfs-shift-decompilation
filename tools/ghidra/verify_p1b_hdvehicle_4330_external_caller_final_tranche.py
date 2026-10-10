#!/usr/bin/env python3
"""Close the final direct external caller tranche for exact HDVehicle+0x4330 carriers."""
from __future__ import annotations
import argparse, hashlib, json, sqlite3, struct
from pathlib import Path

FORMAT="SHIFT.P1B.HDVehicle4330ExternalCallerFinalTranche/1"
RETAIL_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
SQLITE_SHA256="ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED={"SHIFT.GhidraSQLiteIndex/1","SHIFT.GhidraSQLiteIndex/2"}
EXPECTED_FUNCS={
 "0x00aa2850":("FUN_00aa2850",10,"176a39ed845abe7a6fbe51c430190743abeda60e4c62b6f9c3b68280720750d4"),
 "0x00a7063f":("Unwind@00a7063f",14,"3b75e73f266194b6093880f217f9051a42120d6e349d9ecd5a328882bc72afa1"),
 "0x00a72322":("Unwind@00a72322",11,"af667b190a0dca41de8bc5ac0d4ae3a60312d36bec606f9dab50a97e1108191c"),
 "0x00769520":("FUN_00769520",280,"9298d68af33d267227cbabe19e663b22a8ddb1720eee0e44cb7778a2b20bc9f3"),
 "0x0076b130":("FUN_0076b130",321,"d74607c82ee610c9ade7a14d3813df774d5621f541c33d64542371f8e3793430"),
 "0x00798df0":("FUN_00798df0",1581,"88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16"),
}
WINDOWS=[
 (0x00aa2850,"b90037c100e9c66cccff","literal root -> FUN_00769520"),
 (0x00a7063f,"8b4df081c130430000e9035aceff","EH action loads saved parent root +0x4330 -> FUN_00756050"),
 (0x00a7064d,"b8bc1bb700e9d07ee9ff","shared EH handler stub -> FuncInfo 0x00b71bbc"),
 (0x00769520,"558bec6aff684d06a70064a100000000506489250000000051568bf18975f0","FUN_00769520 saves entry ECX at [EBP-0x10] under shared handler"),
 (0x0076b130,"558bec6aff684d06a70064a100000000506489250000000051568bf18d8ea00200008975f0","FUN_0076b130 saves entry ECX at [EBP-0x10] under shared handler"),
 (0x00a72322,"8d8d74dcffffe9233dceff","EH action uses parent stack local EBP-0x238c"),
 (0x00a7234b,"b87c3eb700e9d261e9ff","FUN_00798df0 EH handler stub -> FuncInfo 0x00b73e7c"),
 (0x00798df0,"558bec6aff64a100000000684b23a70050b88023000064892500000000","FUN_00798df0 installs handler 0x00a7234b"),
]

class PEImage:
 def __init__(self,data:bytes):
  self.data=data
  if data[:2]!=b"MZ": raise ValueError("not MZ")
  pe=struct.unpack_from("<I",data,0x3c)[0]
  if data[pe:pe+4]!=b"PE\0\0": raise ValueError("missing PE")
  coff=pe+4; n=struct.unpack_from("<H",data,coff+2)[0]; osz=struct.unpack_from("<H",data,coff+16)[0]; opt=coff+20
  if struct.unpack_from("<H",data,opt)[0]!=0x10b: raise ValueError("not PE32")
  self.base=struct.unpack_from("<I",data,opt+28)[0]; table=opt+osz; self.sections=[]
  for i in range(n):
   o=table+i*40; vs,va,rs,rp=struct.unpack_from("<IIII",data,o+8); self.sections.append((va,max(vs,rs),rp,rs))
 def off(self,va:int)->int:
  rva=va-self.base
  for start,span,raw,_ in self.sections:
   if start<=rva<start+span:return raw+(rva-start)
  raise ValueError(f"VA not mapped: 0x{va:08x}")
 def bytes(self,va:int,n:int)->bytes:
  off=self.off(va); return self.data[off:off+n]
 def u32(self,va:int)->int:return struct.unpack("<I",self.bytes(va,4))[0]
 def count_imm32(self,value:int)->list[int]:
  needle=struct.pack("<I",value); result=[]; pos=0
  while True:
   hit=self.data.find(needle,pos)
   if hit<0:break
   for start,_,raw,raw_size in self.sections:
    if raw<=hit<raw+raw_size:
     result.append(self.base+start+(hit-raw)); break
   pos=hit+1
  return result

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()

def parse_unwind(image:PEImage,funcinfo:int)->dict:
 magic=image.u32(funcinfo); max_state=image.u32(funcinfo+4); unwind_map=image.u32(funcinfo+8); entries=[]
 for index in range(max_state):
  row=unwind_map+index*8
  entries.append((struct.unpack("<i",image.bytes(row,4))[0],image.u32(row+4)))
 return {"magic":magic,"max_state":max_state,"unwind_map":unwind_map,"entries":entries}

def analyze(exe:Path,database:Path)->dict:
 exe_hash,db_hash=sha256(exe),sha256(database)
 if exe_hash!=RETAIL_SHA256:raise ValueError(f"unexpected retail SHA-256: {exe_hash}")
 if db_hash!=SQLITE_SHA256:raise ValueError(f"unexpected SQLite SHA-256: {db_hash}")
 image=PEImage(exe.read_bytes())
 for va,expected,meaning in WINDOWS:
  if image.bytes(va,len(bytes.fromhex(expected))).hex()!=expected:
   raise ValueError(f"retail byte drift at 0x{va:08x}: {meaning}")

 shared=parse_unwind(image,0x00b71bbc)
 if shared["magic"]!=0x19930522 or shared["max_state"]!=10 or shared["unwind_map"]!=0x00b71be0:
  raise ValueError(f"shared FuncInfo drift: {shared!r}")
 if shared["entries"][-1]!=(8,0x00a7063f):
  raise ValueError(f"shared unwind action drift: {shared['entries']!r}")
 stack_local=parse_unwind(image,0x00b73e7c)
 if stack_local["magic"]!=0x19930522 or stack_local["max_state"]!=6 or stack_local["unwind_map"]!=0x00b73ea0:
  raise ValueError(f"FUN_00798df0 FuncInfo drift: {stack_local!r}")
 if (-1,0x00a72322) not in stack_local["entries"]:
  raise ValueError(f"stack-local unwind action missing: {stack_local['entries']!r}")
 if sorted(image.count_imm32(0x00a7064d)) != [0x00769526,0x0076b136]:
  raise ValueError("shared handler parent-reference drift")
 if sorted(image.count_imm32(0x00a7234b)) != [0x00798dfc]:
  raise ValueError("FUN_00798df0 handler parent-reference drift")

 db=sqlite3.connect(database)
 try:
  row=db.execute("SELECT value FROM metadata WHERE key='format'").fetchone(); fmt=None if row is None else row[0]
  if fmt not in SUPPORTED:raise ValueError(f"unsupported SQLite format: {fmt!r}")
  for addr,(name,size,digest) in EXPECTED_FUNCS.items():
   row=db.execute("SELECT name,raw_json FROM functions WHERE lower(address)=?",(addr,)).fetchone()
   if row is None:raise ValueError(f"missing function {addr}")
   raw=json.loads(row[1])
   if row[0]!=name or int(raw.get("size") or -1)!=size or raw.get("mnemonic_sha256")!=digest:
    raise ValueError(f"function identity drift: {addr}")
  calls=[json.loads(row[0]) for row in db.execute("SELECT raw_json FROM calls")]
  expected=sorted([
   ("0x00aa2850","0x00aa2855","0x00769520"),
   ("0x00a7063f","0x00a70648","0x00756050"),
   ("0x00a72322","0x00a72328","0x00756050"),
  ])
  sources={row[0] for row in expected}
  got=sorted((str(rec.get("from_function") or "").lower(),str(rec.get("instruction") or "").lower(),str(rec.get("to") or "").lower())
             for rec in calls if rec.get("indirect") is not True
             and str(rec.get("from_function") or "").lower() in sources
             and str(rec.get("to") or "").lower() in {"0x00769520","0x00756050"})
  if got!=expected:raise ValueError(f"remaining call surface drift: {got!r}")
 finally:db.close()

 return {
  "format":FORMAT,"version":1,"ready":True,"owner":"Process 1B / P1.3B",
  "authority":{"platform":"PC retail 1.02","retail_executable_sha256":exe_hash,"ghidra_sqlite_sha256":db_hash,
               "retail_machine_transfer_adjudicates":True,"sqlite_role":"call inventory/fingerprints only"},
  "upstream_contracts":["SHIFT.P1B.HDVehicle4330ExternalCallerTranche2/1","SHIFT.HDVehicle64e8RootDerived4330MaterializerPersistenceClosure/1"],
  "fun_00aa2850":{"site":"0x00aa2855 -> FUN_00769520","receiver":"literal ECX=0x00c13700 HDVehicle root","preexisting_hdvehicle_4330_alias":False},
  "unwind_00a7063f":{
   "site":"0x00a70648 -> FUN_00756050","shared_funcinfo":"0x00b71bbc","unwind_state":8,
   "enclosing_exact_root_functions":["FUN_00769520","FUN_0076b130"],
   "enclosing_handler_pushes":["0x00769526 -> 0x00a7064d","0x0076b136 -> 0x00a7064d"],
   "saved_root_proof":"both parents execute ESI=ECX then [EBP-0x10]=ESI",
   "action":"ECX=[EBP-0x10]; ECX+=0x4330; tail FUN_00756050",
   "classification":"positive exceptional root-derived +0x4330 materializer; not an unknown/pre-existing alias entry",
   "exceptional_root_derived_4330_materializer":True,
  },
  "unwind_00a72322":{
   "site":"0x00a72328 -> FUN_00756050","enclosing_function":"FUN_00798df0","enclosing_funcinfo":"0x00b73e7c",
   "handler_push":"0x00798dfc -> 0x00a7234b","receiver":"LEA ECX,[EBP-0x238c] parent stack local","preexisting_hdvehicle_4330_alias":False,
  },
  "adjudication":{
   "external_caller_final_tranche_complete":True,"cumulative_resolved_external_caller_count":7,"cumulative_resolved_external_callsite_count":11,
   "remaining_external_caller_count":0,"external_direct_incoming_receiver_provenance_complete":True,
   "external_direct_incoming_preexisting_4330_alias_found":False,"exceptional_root_derived_4330_materializer_found":True,
   "exceptional_root_derived_4330_materializer_bounded":True,"indirect_entry_into_carriers_ruled_out":False,
   "global_runtime_derived_4330_alias_surface_complete":False,"manager_374_join_to_hdvehicle_4330_complete":False,
   "last_literal_0x004b86cf_rejected":False,"p1_3_control_producer_complete":False,"external_provider_count":7,
  },
  "limits":[
   "This closes all eleven direct external callsites into the 15 exact HDVehicle+0x4330 carrier set.",
   "Unwind@00a7063f is admitted as a real exceptional root-derived +0x4330 materializer, not rejected by label.",
   "Indirect entry, runtime-generated/copied function pointers and other non-root-derived data aliases remain open.",
   "The manager+0x374 identity join and final literal candidate remain fail-closed."
  ],
  "next_step":"Remove direct external incoming calls from the 0x4330 frontier. Continue only indirect-entry/runtime-generated pointer paths and other non-root-derived runtime 0x4330 aliases before attempting the manager identity join."
 }

def main()->int:
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("exe",type=Path); p.add_argument("database",type=Path); p.add_argument("--output",type=Path); a=p.parse_args()
 try:result=analyze(a.exe,a.database)
 except ValueError as exc:p.error(str(exc))
 text=json.dumps(result,indent=2,sort_keys=True)+"\n"
 if a.output:a.output.write_text(text,encoding="utf-8")
 else:print(text,end="")
 return 0
if __name__=="__main__":raise SystemExit(main())
