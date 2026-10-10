#!/usr/bin/env python3
"""Bound indirect-call edges inside the already-proven slot3 exact-carrier set."""
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3ExactCarrierIndirectCallSurface/1"
SQLITE_SHA256="ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED={"SHIFT.GhidraSQLiteIndex/1","SHIFT.GhidraSQLiteIndex/2"}
CARRIERS={
 "0x00758b50":"FUN_00758b50","0x00755950":"FUN_00755950",
 "0x00770e80":"FUN_00770e80","0x00755a60":"FUN_00755a60",
 "0x00752fc0":"FUN_00752fc0","0x00760b50":"FUN_00760b50",
 "0x00763570":"FUN_00763570","0x00755f80":"FUN_00755f80",
 "0x0076d100":"FUN_0076d100","0x00758810":"FUN_00758810",
 "0x00769ef0":"FUN_00769ef0","0x007675f0":"FUN_007675f0",
 "0x007682c0":"FUN_007682c0","0x00766510":"FUN_00766510",
 "0x00758fc0":"FUN_00758fc0","0x00765c40":"FUN_00765c40",
}
EXPECTED={
 "0x00758b50":(1136,"3ef5ee12cb0af2f75b5e039dacaf95e42b40002cb681dc1cf00556c6bebe1eeb"),
 "0x00755950":(66,"976369508b2d92e05d62cfb8d489f19e40c1ec4a145203c84346d5abe89089b8"),
 "0x00770e80":(1183,"509d932c8a3c397f69fe91acecadef2bc148a05237a947c226d9ff039860514e"),
 "0x00755a60":(1297,"b54457da18192fdb856f0a176dbea0d8d017b32de078e46c36fa1dea2833194c"),
 "0x00752fc0":(37,"850d8c8eb123598b8e54c2ee199c82f9bb0879ad7ba3d9ca1f7e9018c968321e"),
 "0x00760b50":(531,"31f53fc3a79ca1df57a7a96e470cdca64ffb590fbbe47169964df348421d447b"),
 "0x00763570":(3277,"613c21748d8b549f1d94d93cd8bada5b2a75763c58b64ba57691245aa14e37d3"),
 "0x00755f80":(132,"35c5d9528694a35a282cccde02739d5b922a3ddeeba2ef1bce57464dd23c1135"),
 "0x0076d100":(508,"ab1d8a14406c88e02240c03b0a636b7433df72e9dfaec4654746d19e6ba6de5c"),
 "0x00758810":(347,"dfc311f47d9922ab17b799f2f6840e10dfd1e5118c0bb39afbc2725691db1cf6"),
 "0x00769ef0":(774,"1ee3fee50472079154d2029eb4c861b3d1b1eda895347c531316678b7e15d1bf"),
 "0x007675f0":(1340,"8d112f82c1deec91c6a197002fcf37b5201dc3377e0cfd9bb23d795afbbf72d7"),
 "0x007682c0":(335,"f60c733cc0d0b3c755b3104953d1dc1d623d15f33978a6cbe50de7947b7f5d34"),
 "0x00766510":(4310,"3559c0125cdda2b171b357d35392d93eaba68db86899ec5b44730a6533b91098"),
 "0x00758fc0":(364,"515ba898241d40c003ea49958052af13cdf765af3dc66d275b5238447e3b395b"),
 "0x00765c40":(2249,"dcebcb4d773245033351265d65f7e2212cb60d097f323b84379bd2000a5a1df4"),
}

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def analyze(database:Path)->dict:
 digest=sha256(database)
 if digest!=SQLITE_SHA256:raise ValueError(f'unexpected SQLite SHA-256: {digest}')
 db=sqlite3.connect(database)
 try:
  row=db.execute("SELECT value FROM metadata WHERE key='format'").fetchone();fmt=None if row is None else row[0]
  if fmt not in SUPPORTED:raise ValueError(f'unsupported SQLite format: {fmt!r}')
  admitted=[]
  for addr,name in CARRIERS.items():
   row=db.execute("SELECT name,raw_json FROM functions WHERE lower(address)=?",(addr,)).fetchone()
   if row is None:raise ValueError(f'missing carrier {addr}')
   raw=json.loads(row[1]);size,digest_expected=EXPECTED[addr]
   if row[0]!=name or int(raw.get('size') or -1)!=size or raw.get('mnemonic_sha256')!=digest_expected:
    raise ValueError(f'carrier identity drift: {addr}')
   admitted.append({'address':addr,'name':name,'size':size,'mnemonic_sha256':digest_expected})
  total_indirect=0;carrier_indirect=[]
  for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
   rec=json.loads(raw_text)
   if rec.get('indirect') is not True:continue
   total_indirect+=1
   src=str(rec.get('from_function') or '').lower()
   if src in CARRIERS:
    carrier_indirect.append({'from_function':src,'from_name':rec.get('from_name'),'instruction':str(rec.get('instruction') or '').lower()})
  if total_indirect<=0:raise ValueError('SQLite no longer exposes indirect call edges')
  return {
   'format':FORMAT,'version':1,'ready':True,'owner':'Process 1D / P1.3D',
   'authority':{'platform':'PC retail 1.02','ghidra_sqlite_sha256':digest,'ghidra_sqlite_format':fmt,'sqlite_is_navigation_index':True},
   'carrier_set':{'count':len(admitted),'functions':admitted,'semantic_identity_source':'merged P1D exact-root/exact-wheel machine contracts including SHIFT.P1D.Slot3Fun00765c40CarrierHandoff/1'},
   'indirect_surface':{'whole_index_indirect_call_edge_count':total_indirect,'carrier_indirect_call_edge_count':len(carrier_indirect),'carrier_indirect_call_edges':carrier_indirect},
   'adjudication':{
    'sqlite_indirect_call_edge_class_present':True,
    'known_exact_carrier_indirect_call_edge_surface_complete':True,
    'known_exact_carrier_indirect_call_edge_surface_empty':len(carrier_indirect)==0,
    'stored_or_escaped_aliases_ruled_out':False,
    'indirect_entry_into_carriers_ruled_out':False,
    'callbacks_registered_outside_carriers_ruled_out':False,
    'global_indirect_dispatch_ruled_out':False,
    'slot3_writer_provenance_proven':False,
    'p1_3d_complete':False,
    'p1_3_control_producer_complete':False,
    'external_provider_count':7,
   },
   'limits':[
    'This is only the Ghidra-recorded CALLIND surface whose caller is one of the 16 already-proven exact carrier functions.',
    'Zero CALLIND rows does not rule out pointers stored for later use, callbacks invoked elsewhere, indirect entry into a carrier, or aliases created in other functions.',
    'Function fingerprints and call rows are navigation/cross-check evidence; existing merged machine contracts remain semantic authority for selected-object identity.'
   ],
   'next_step':'Trace stores/escapes of exact HDVehicle or selected-wheel pointers from the proven carrier set, then join any escaped pointer to its later indirect/callback consumer before changing slot3 gates.'
  }
 finally:db.close()

def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('database',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=analyze(a.database)
 except ValueError as e:p.error(str(e))
 t=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(t,encoding='utf-8')
 else:print(t,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())
