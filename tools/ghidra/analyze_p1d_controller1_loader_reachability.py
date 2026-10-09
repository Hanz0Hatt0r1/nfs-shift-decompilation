#!/usr/bin/env python3
"""Bound direct loader/module-handle calls reachable from Controller #1.

Navigation evidence only: direct loader reachability does not prove manual/native APC resolution.
"""
from __future__ import annotations
import argparse, hashlib, json, sqlite3
from collections import deque
from pathlib import Path

FORMAT="SHIFT.P1D.Controller1LoaderReachability/1"
WORKER="0x00662880"
TARGETS={"getmodulehandlea","getmodulehandlew","loadlibrarya","loadlibraryw","freelibrary"}

def digest(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def graph_and_calls(db):
    graph={}; calls=[]
    for (raw,) in db.execute('SELECT raw_json FROM calls'):
        r=json.loads(raw); src=r.get('from_function') or r.get('caller_address') or r.get('caller'); dst=r.get('to') or r.get('callee_address') or r.get('callee')
        if src and dst and not r.get('indirect'): graph.setdefault(str(src).lower(),[]).append(str(dst).lower())
        name=str(r.get('to_name') or r.get('callee_name') or r.get('callee') or '')
        if name.casefold() in TARGETS and not r.get('indirect'): calls.append(r)
    return graph,calls

def tree(graph):
    prev={WORKER:None}; q=deque([WORKER])
    while q:
        u=q.popleft()
        for v in graph.get(u,[]):
            if v not in prev: prev[v]=u; q.append(v)
    return prev

def path(prev,t):
    t=t.lower()
    if t not in prev:return []
    p=[t]
    while prev[p[-1]] is not None:p.append(prev[p[-1]])
    return list(reversed(p))

def analyze(db_path:Path)->dict:
    db=sqlite3.connect(db_path); db.row_factory=sqlite3.Row
    try:
        fmt=db.execute("SELECT value FROM metadata WHERE key='format'").fetchone(); graph,calls=graph_and_calls(db); prev=tree(graph); rows=[]
        for r in calls:
            caller=str(r.get('from_function') or r.get('caller_address') or r.get('caller') or '').lower(); name=str(r.get('to_name') or r.get('callee_name') or r.get('callee') or '')
            local=[{"address":x['address'],"value":x['value']} for x in db.execute('SELECT address,value FROM strings WHERE lower(containing_function)=lower(?) ORDER BY address',(caller,))]
            rows.append({"target_name":name,"caller":caller,"callsite":r.get('instruction') or r.get('callsite'),"direct_worker_reachable":caller in prev,"shortest_direct_path":path(prev,caller),"local_strings":local})
    finally: db.close()
    rows.sort(key=lambda x:str(x['callsite']))
    reachable=[r for r in rows if r['direct_worker_reachable']]
    return {"format":FORMAT,"version":1,"ready":True,"owner":"Process 1D / P1.3D","authority":{"source_index_format":fmt[0] if fmt else 'unknown',"source_index_sha256":digest(db_path),"index_is_navigation_evidence_only":True},"worker":WORKER,"counts":{"direct_loader_call_count":len(rows),"direct_worker_reachable_loader_call_count":len(reachable)},"reachable_calls":reachable,"all_calls":rows,"adjudication":{"direct_loader_surface_bounded":True,"reachable_loader_surface_adds_new_apc_resolution_candidate":False,"manual_or_hashed_resolution_ruled_out":False,"indirect_loader_or_resolver_surface_ruled_out":False,"native_or_syscall_apc_injection_ruled_out":False,"controller1_timing_exhaustive":False,"p1_3d_complete":False,"external_provider_count":7},"next_step":"Continue #1699/#1712 native/manual primitive adjudication; direct reachable loader calls add no new APC resolution candidate beyond already bounded resolver contexts."}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('database',type=Path); ap.add_argument('--output',type=Path); a=ap.parse_args(); p=analyze(a.database); s=json.dumps(p,indent=2,sort_keys=True)+'\n'; a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__': main()
