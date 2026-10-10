#!/usr/bin/env python3
"""Close null SetWaitableTimer/WSARecv callbacks in the P1B non-thread frontier."""
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from pathlib import Path
FORMAT='SHIFT.P1B.HDVehicle4330NonThreadCallbackTranche2/1'
SQLITE_SHA256='ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e'
SOURCE_SHA256='512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9'
SUPPORTED={'SHIFT.GhidraSQLiteIndex/1','SHIFT.GhidraSQLiteIndex/2'}
EXPECTED={'SetWaitableTimer':{'0x0099882b','0x00998e13'},'WSARecv':{'0x005fdd21'}}
SOURCE_FRAGMENTS=[
 'pfnCompletionRoutine = (PTIMERAPCROUTINE)0x0;',
 'SetWaitableTimer(hTimer,&local_58,(LONG)uVar9,pfnCompletionRoutine,',
 'p_Var6 = unaff_EBX;\n                lpArgToCompletionRoutine = unaff_EBX;\n                fResume = unaff_EBX;',
 'WSARecv(*(undefined4 *)(in_EAX + 0x18),&local_8,1,piVar1,puVar2,in_EAX + 0x54,0)'
]
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
def rows(db,api):
 out=set()
 for (raw,) in db.execute('select raw_json from calls'):
  r=json.loads(raw)
  if r.get('indirect') is not True and r.get('to_name')==api:out.add(str(r.get('instruction')).lower())
 return out
def analyze(database,source):
 dh,sh=sha(database),sha(source)
 if dh!=SQLITE_SHA256:raise ValueError(f'unexpected SQLite SHA-256: {dh}')
 if sh!=SOURCE_SHA256:raise ValueError(f'unexpected source SHA-256: {sh}')
 db=sqlite3.connect(database)
 try:
  fmt=db.execute("select value from metadata where key='format'").fetchone()
  if not fmt or fmt[0] not in SUPPORTED:raise ValueError(f'unsupported SQLite format: {fmt!r}')
  got={a:rows(db,a) for a in EXPECTED}
 finally:db.close()
 if got!=EXPECTED:raise ValueError(f'callback surface drift: {got!r}')
 text=source.read_text(encoding='utf-8',errors='strict')
 miss=[x for x in SOURCE_FRAGMENTS if x not in text]
 if miss:raise ValueError(f'source fragment drift: {miss!r}')
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1B / P1.3B','authority':{'ghidra_sqlite_sha256':dh,'shift_exe_c_sha256':sh},'surface':{'resolved_callsite_count':3,'remaining_callsite_count':1,'resolved_sites':[{'api':'SetWaitableTimer','callsite':'0x0099882b','callback':'NULL'},{'api':'SetWaitableTimer','callsite':'0x00998e13','callback':'NULL'},{'api':'WSARecv','callsite':'0x005fdd21','callback':'NULL'}],'remaining_site':{'api':'WSARecvFrom','callsite':'0x005fdd09'}},'adjudication':{'setwaitabletimer_completion_subset_complete':True,'wsarecv_completion_subset_complete':True,'nonthread_callback_argument_provenance_complete':False,'runtime_callback_registration_ruled_out':False,'indirect_entry_into_carriers_ruled_out':False,'manager_374_join_to_hdvehicle_4330_complete':False,'last_literal_0x004b86cf_rejected':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['WSARecvFrom at 0x005fdd09 remains unresolved because the decompiler export does not expose a trustworthy final completion-routine argument.'],'next_step':'Resolve WSARecvFrom callback argument from retail machine bytes or an authoritative signature-correct export, then continue generic runtime function-pointer stores/copies.'}
def main():
 p=argparse.ArgumentParser();p.add_argument('database',type=Path);p.add_argument('source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=analyze(a.database,a.source)
 except ValueError as e:p.error(str(e))
 s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
