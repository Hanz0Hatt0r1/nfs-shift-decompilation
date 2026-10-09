#!/usr/bin/env python3
"""Join Controller #1 direct callgraph reachability with direct GetProcAddress callers."""
from __future__ import annotations
import argparse, json, sqlite3
from collections import defaultdict, deque
from pathlib import Path

FORMAT = "SHIFT.P1D.Controller1DirectGetProcReachability/1"
APC_NAMES = {"QueueUserAPC","NtQueueApcThread","NtQueueApcThreadEx","ZwQueueApcThread","RtlQueueApcWow64Thread","SetWaitableTimerEx"}


def load_calls(db):
    return [json.loads(r[0]) for r in db.execute("select raw_json from calls")]


def analyze(db_path: Path, start: str = "0x00662880") -> dict:
    db = sqlite3.connect(db_path)
    try:
        meta = dict(db.execute("select key,value from metadata"))
        funcs = {r[0] for r in db.execute("select address from functions")}
        calls = load_calls(db)
        direct_getproc = [r for r in calls if not r.get("indirect") and r.get("to_name") == "GetProcAddress"]
        by = defaultdict(list)
        for r in direct_getproc: by[r.get("from_function")].append(r)
        adj = defaultdict(set)
        for r in calls:
            if r.get("indirect"): continue
            s,t = r.get("from_function"), r.get("to")
            if s and t in funcs: adj[s].add(t)
        parent={start:None}; q=deque([start])
        while q:
            u=q.popleft()
            for v in adj.get(u,()):
                if v not in parent: parent[v]=u; q.append(v)
        def path(t):
            out=[]
            while t is not None: out.append(t); t=parent[t]
            return list(reversed(out))
        reachable=[]
        for fn in sorted(set(by)&set(parent)):
            recs=by[fn]
            strings=[{"value":v,"address":a} for v,a in db.execute("select value,address from strings where containing_function=? order by address",(fn,))]
            hits=[x["value"] for x in strings if x["value"] in APC_NAMES]
            reachable.append({"function":fn,"name":recs[0].get("from_name"),"getprocaddress_callsites":[r.get("instruction") for r in recs],"direct_path_from_controller1":path(fn),"local_defined_strings":strings,"local_apc_name_hits":hits})
        return {
            "format":FORMAT,"version":1,"ready":True,
            "authority":{"sqlite_index_format":meta.get("format"),"source_dir":meta.get("source_dir")},
            "controller1":{"worker":"FUN_00662880","address":start,"direct_reachable_internal_function_count":len(parent)},
            "getprocaddress_surface":{"direct_getprocaddress_callsite_count":len(direct_getproc),"direct_getprocaddress_caller_function_count":len(by),"reachable_caller_function_count":len(reachable),"reachable_functions":reachable},
            "adjudication":{"reachable_direct_getprocaddress_functions_have_local_apc_literal_names":any(x["local_apc_name_hits"] for x in reachable),"reachable_direct_named_resolver_local_literal_apc_surface_rejected":not any(x["local_apc_name_hits"] for x in reachable),"nonlocal_runtime_generated_or_hashed_names_ruled_out":False,"manual_export_walking_ruled_out":False,"native_or_syscall_apc_injection_ruled_out":False,"controller1_timing_exhaustive":False,"p1_3d_complete":False,"external_provider_count":7}
        }
    finally: db.close()


def main():
    p=argparse.ArgumentParser(); p.add_argument("database",type=Path); p.add_argument("--output",type=Path); a=p.parse_args()
    out=json.dumps(analyze(a.database),indent=2,sort_keys=True)+"\n"
    a.output.write_text(out,encoding="utf-8") if a.output else print(out,end="")
    return 0
if __name__ == "__main__": raise SystemExit(main())
