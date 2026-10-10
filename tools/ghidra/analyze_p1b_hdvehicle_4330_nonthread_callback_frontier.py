#!/usr/bin/env python3
"""Inventory finite non-thread callback-registration API callsites for P1.3B."""
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path

FORMAT="SHIFT.P1B.HDVehicle4330NonThreadCallbackFrontier/1"
SQLITE_SHA256="ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SUPPORTED={"SHIFT.GhidraSQLiteIndex/1","SHIFT.GhidraSQLiteIndex/2"}
EXPECTED={
 "RegisterClassExW":["0x00634b89","0x00634c52","0x00634c93"],
 "RegisterClassA":[],
 "SetWaitableTimer":["0x0099882b","0x00998e13"],
 "ReadFileEx":["0x006558d5","0x00655c15"],
 "WriteFileEx":["0x006559df","0x00655dca"],
 "WSARecv":["0x005fdd21"],
 "WSARecvFrom":["0x005fdd09"],
}
# RegisterClassA is retained as an explicit API family even when this pinned SQLite
# records no direct callsites; this distinguishes zero from unexamined.
CARRIERS={
 "0x00758b50","0x00755950","0x00770e80","0x00755a60","0x00752fc0",
 "0x00760b50","0x00763570","0x00755f80","0x0076d100","0x00758810",
 "0x00769ef0","0x007675f0","0x007682c0","0x00766510","0x00758fc0",
}

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def analyze(database:Path)->dict:
 digest=sha256(database)
 if digest!=SQLITE_SHA256: raise ValueError(f'unexpected SQLite SHA-256: {digest}')
 db=sqlite3.connect(database)
 try:
  row=db.execute("SELECT value FROM metadata WHERE key='format'").fetchone(); fmt=None if row is None else row[0]
  if fmt not in SUPPORTED: raise ValueError(f'unsupported SQLite format: {fmt!r}')
  rows=[]
  for (raw_text,) in db.execute("SELECT raw_json FROM calls"):
   r=json.loads(raw_text); name=str(r.get('to_name') or '')
   if name not in EXPECTED: continue
   rows.append({
    'api':name,'caller':str(r.get('from_function') or '').lower(),
    'caller_name':r.get('from_name'),'callsite':str(r.get('instruction') or '').lower(),
    'direct':r.get('indirect') is False,
   })
  if any(not r['direct'] for r in rows): raise ValueError('callback API inventory gained indirect call rows')
  by_api={name:sorted(r['callsite'] for r in rows if r['api']==name) for name in EXPECTED}
  for name,expected in EXPECTED.items():
   if by_api[name]!=expected: raise ValueError(f'{name} callsite drift: {by_api[name]!r}')
  carrier_callers=sorted({r['caller'] for r in rows if r['caller'] in CARRIERS})
  return {
   'format':FORMAT,'version':1,'ready':True,'owner':'Process 1B / P1.3B',
   'authority':{'platform':'PC retail 1.02','ghidra_sqlite_sha256':digest,'ghidra_sqlite_format':fmt,'sqlite_is_navigation_crosscheck_only':True},
   'api_surface':{
    'families':list(EXPECTED),'direct_callsite_count':len(rows),'rows':sorted(rows,key=lambda r:(r['api'],r['callsite'])),
    'exact_carrier_caller_count':len(carrier_callers),'exact_carrier_callers':carrier_callers,
   },
   'adjudication':{
    'nonthread_callback_api_callsite_inventory_complete':True,
    'callback_argument_provenance_complete':False,
    'exact_4330_carrier_registered_as_nonthread_callback':False,
    'runtime_callback_registration_ruled_out':False,
    'indirect_entry_into_carriers_ruled_out':False,
    'global_runtime_derived_4330_alias_surface_complete':False,
    'manager_374_join_to_hdvehicle_4330_complete':False,
    'last_literal_0x004b86cf_rejected':False,
    'p1_3_control_producer_complete':False,
    'external_provider_count':7,
   },
   'limits':[
    'This contract inventories direct calls to selected callback-capable Win32/Winsock APIs; it does not yet prove each callback argument value.',
    'Zero exact-carrier callers is not evidence that no carrier address is passed by another function.',
    'Other callback families and generic function-pointer stores remain outside this subset.'
   ],
   'next_step':'Adjudicate callback arguments at the 10 pinned callsites, beginning with RegisterClassExW WndProc and ReadFileEx/WriteFileEx completion routines, then SetWaitableTimer and Winsock completion parameters.'
  }
 finally: db.close()

def main()->int:
 p=argparse.ArgumentParser(description=__doc__); p.add_argument('database',type=Path); p.add_argument('--output',type=Path); a=p.parse_args()
 try:r=analyze(a.database)
 except ValueError as e:p.error(str(e))
 text=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(text,encoding='utf-8')
 else:print(text,end='')
 return 0
if __name__=='__main__': raise SystemExit(main())
