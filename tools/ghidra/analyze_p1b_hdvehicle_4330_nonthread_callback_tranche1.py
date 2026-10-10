#!/usr/bin/env python3
"""Close the first non-thread callback tranche for exact HDVehicle+0x4330 carriers."""
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path

FORMAT="SHIFT.P1B.HDVehicle4330NonThreadCallbackTranche1/1"
SQLITE_SHA256="ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
SOURCE_SHA256="512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
SUPPORTED={"SHIFT.GhidraSQLiteIndex/1","SHIFT.GhidraSQLiteIndex/2"}
EXACT_CARRIERS={0x00758B50,0x00755950,0x00770E80,0x00755A60,0x00752FC0,0x00760B50,0x00763570,0x00755F80,0x0076D100,0x00758810,0x00769EF0,0x007675F0,0x007682C0,0x00766510,0x00758FC0}
EXPECTED={
 "RegisterClassExW":{"0x00634b89","0x00634c52","0x00634c93"},
 "ReadFileEx":{"0x006558d5","0x00655c15"},
 "WriteFileEx":{"0x006559df","0x00655dca"},
}
CALLBACKS={"FUN_00634870":0x00634870,"lpCompletionRoutine_006553e0":0x006553e0,"lpCompletionRoutine_00655410":0x00655410}
SOURCE_FRAGMENTS=[
 "*(code **)((int)this + 0xb0) = FUN_00634870;",
 "*(code **)((int)this + 0xe0) = FUN_00634870;",
 "RegisterClassExW((WNDCLASSEXW *)((int)this + 0xa8))",
 "RegisterClassExW((WNDCLASSEXW *)((int)this + 0xd8))",
 "(LPOVERLAPPED)(param_1 + 0x2a),lpCompletionRoutine_006553e0)",
 "(LPOVERLAPPED)((int)this + 0xa8),\n                       lpCompletionRoutine_006553e0)",
 "(LPOVERLAPPED)(param_1 + 0x2a),lpCompletionRoutine_00655410)",
 "(LPOVERLAPPED)((int)this + 0xa8),\n                      lpCompletionRoutine_00655410)",
]

def sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def calls(db,api):
 out=set()
 for (raw,) in db.execute('select raw_json from calls'):
  r=json.loads(raw)
  if r.get('indirect') is not True and r.get('to_name')==api: out.add(str(r.get('instruction')).lower())
 return out

def analyze(database:Path,source:Path)->dict:
 dh,sh=sha256(database),sha256(source)
 if dh!=SQLITE_SHA256: raise ValueError(f'unexpected SQLite SHA-256: {dh}')
 if sh!=SOURCE_SHA256: raise ValueError(f'unexpected source SHA-256: {sh}')
 db=sqlite3.connect(database)
 try:
  fmt=db.execute("select value from metadata where key='format'").fetchone()
  if not fmt or fmt[0] not in SUPPORTED: raise ValueError(f'unsupported SQLite format: {fmt!r}')
  got={api:calls(db,api) for api in EXPECTED}
 finally: db.close()
 if got!=EXPECTED: raise ValueError(f'callback callsite surface drift: {got!r}')
 text=source.read_text(encoding='utf-8',errors='strict')
 missing=[x for x in SOURCE_FRAGMENTS if x not in text]
 if missing: raise ValueError(f'callback source fragment drift: {missing!r}')
 hits={n:a for n,a in CALLBACKS.items() if a in EXACT_CARRIERS}
 if hits: raise ValueError(f'exact carrier callback hit: {hits!r}')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1B / P1.3B',
  'authority':{'platform':'PC retail 1.02','ghidra_sqlite_sha256':dh,'shift_exe_c_sha256':sh,'source_is_navigation_crosscheck':True},
  'surface':{'resolved_callsite_count':7,'frontier_callsite_count':11,'remaining_callsite_count':4,'resolved_callback_count':3,
   'resolved_callbacks':[{'name':n,'address':f'0x{a:08x}'} for n,a in sorted(CALLBACKS.items(),key=lambda x:x[1])],
   'remaining_apis':['SetWaitableTimer','WSARecv','WSARecvFrom']},
  'adjudication':{'wndproc_registration_subset_complete':True,'readfileex_writefileex_completion_subset_complete':True,'exact_4330_carrier_callback_found':False,
   'nonthread_callback_argument_provenance_complete':False,'runtime_callback_registration_ruled_out':False,'indirect_entry_into_carriers_ruled_out':False,
   'global_runtime_derived_4330_alias_surface_complete':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,
   'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['This closes only the three RegisterClassExW WndProc registrations and four ReadFileEx/WriteFileEx completion registrations from the pinned frontier.','SetWaitableTimer and Winsock completion parameters remain open.','Decompiler source is used only to identify the explicit callback values selected at already-inventoried callsites.'],
  'next_step':'Adjudicate the two SetWaitableTimer completion routines and two Winsock completion-parameter callsites, then continue generic runtime function-pointer stores/copies.'}

def main():
 p=argparse.ArgumentParser(); p.add_argument('database',type=Path); p.add_argument('source',type=Path); p.add_argument('--output',type=Path); a=p.parse_args()
 try:r=analyze(a.database,a.source)
 except ValueError as e:p.error(str(e))
 s=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(s,encoding='utf-8')
 else:print(s,end='')
if __name__=='__main__': main()
