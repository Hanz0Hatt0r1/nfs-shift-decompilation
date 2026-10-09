#!/usr/bin/env python3
"""Inventory shallow straight-line unrolled ordinary-MOV copy sequences for P1.3A.

Navigation evidence only. The scan follows direct calls from the four recovered
wheel/physics roots to depth four, excludes instructions covered by backward
branch loops, and finds clobber-safe memory-load -> register -> memory-store
sequences. A candidate cluster requires at least two stores to the same
non-stack destination base and contiguous destination coverage of at least
8 bytes. Zero-initialization is intentionally excluded and handled separately.
"""
from __future__ import annotations
import argparse, bisect, collections, hashlib, json, re, sqlite3, subprocess
from pathlib import Path

FORMAT = "SHIFT.P1A.P13ASlot01UnrolledMovCopyFrontier/1"
SUPPORTED_INDEXES = {"SHIFT.GhidraSQLiteIndex/1", "SHIFT.GhidraSQLiteIndex/2"}
ROOTS = ("FUN_00758b50","FUN_0076d100","FUN_00763570","FUN_00770e80")
REGS = {"eax","ebx","ecx","edx","esi","edi","ebp","esp"}
WRITE_MNEMONICS = {"mov","lea","add","sub","inc","dec","xor","and","or","shl","shr","sar","imul"}
INSN_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([^\s]+)\s*(.*)$")
TARGET_RE = re.compile(r"0x([0-9a-fA-F]+)")
MEM_RE = re.compile(r"(?:(byte|word|dword|qword) ptr )?\[([^\]]+)\]", re.I)


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def split_ops(text: str):
    return [p.strip() for p in text.split(',',1)] if ',' in text else [text.strip()]


def reg(text: str):
    v=text.lower().strip()
    v=re.sub(r"^(?:byte|word|dword|qword) ptr\s+", "", v)
    return v if v in REGS else None


def mem_info(op: str):
    mm=MEM_RE.search(op.lower().strip())
    if not mm: return None
    width={"byte":1,"word":2,"dword":4,"qword":8,None:None}[mm.group(1).lower() if mm.group(1) else None]
    expr=mm.group(2).replace(' ','')
    terms=re.findall(r'[+-]?[^+-]+',expr)
    const=0; nonconst=[]
    for term in terms:
        sign=-1 if term.startswith('-') else 1
        raw=term[1:] if term[:1] in '+-' else term
        if re.fullmatch(r'0x[0-9a-f]+|\d+',raw): const += sign*int(raw,0)
        else: nonconst.append(('-' if sign<0 else '')+raw)
    base='+'.join(nonconst).replace('+-','-')
    return width,base,const,expr


def index_format(db):
    row=db.execute("SELECT value FROM metadata WHERE key='format'").fetchone()
    if not row or row[0] not in SUPPORTED_INDEXES: raise ValueError("unsupported/missing SQLite format")
    return str(row[0])


def direct_graph(db, fmt):
    adj=collections.defaultdict(list); sites=collections.defaultdict(list)
    if fmt.endswith('/1'):
        for (raw,) in db.execute('SELECT raw_json FROM calls'):
            r=json.loads(raw)
            if r.get('indirect'): continue
            a=str(r.get('from_name') or r.get('from_function') or '')
            b=str(r.get('to_name') or r.get('to') or '')
            s=str(r.get('instruction') or r.get('callsite') or '')
            if a and b: adj[a].append(b); sites[(a,b)].append(s)
    else:
        for a,b,s,k,ind in db.execute('SELECT caller,callee,callsite,kind,indirect FROM calls'):
            if ind or str(k).lower()=='indirect' or not a or not b: continue
            a,b=str(a),str(b); adj[a].append(b); sites[(a,b)].append(str(s or ''))
    return adj,sites


def reachability(adj,max_depth=4):
    best={}; paths={}
    for root in ROOTS:
        dist={root:0}; parent={}; q=collections.deque([root])
        while q:
            n=q.popleft()
            if dist[n]>=max_depth: continue
            for c in adj.get(n,[]):
                if c in dist: continue
                dist[c]=dist[n]+1; parent[c]=n; q.append(c)
        for n,d in dist.items():
            if d>=best.get(n,1<<30): continue
            best[n]=d; p=[n]; cur=n
            while cur!=root: cur=parent[cur]; p.append(cur)
            paths[n]=list(reversed(p))
    return best,paths


def sized_ranges(db, reachable):
    out=[]
    for address,name,raw in db.execute('SELECT address,name,raw_json FROM functions'):
        if name not in reachable or not address: continue
        size=int(json.loads(raw).get('size') or 0)
        if size<=0: continue
        start=int(str(address),16); out.append((start,start+size,str(name),reachable[str(name)]))
    return sorted(out)


def disassemble(exe: Path):
    return subprocess.run(['objdump','-d','-M','intel',str(exe)],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout


def parse_instructions(text,ranges):
    starts=[r[0] for r in ranges]; out=collections.defaultdict(list)
    for line in text.splitlines():
        m=INSN_RE.match(line)
        if not m: continue
        a=int(m.group(1),16); i=bisect.bisect_right(starts,a)-1
        if i<0: continue
        s,e,n,_=ranges[i]
        if s<=a<e: out[n].append((a,m.group(2).lower(),m.group(3).strip()))
    return out


def backward_intervals(instrs):
    intervals=[]
    for i,(a,mn,ops) in enumerate(instrs):
        if not mn.startswith('j'): continue
        mt=TARGET_RE.search(ops)
        if not mt: continue
        target=int(mt.group(1),16)
        if target>=a: continue
        j=next((k for k,row in enumerate(instrs) if row[0]>=target),None)
        if j is not None: intervals.append((j,i))
    return intervals


def in_loop(i,intervals): return any(a<=i<=b for a,b in intervals)


def transfer_hits(instrs):
    intervals=backward_intervals(instrs); last_load={}; hits=[]
    for i,(addr,mn,ops) in enumerate(instrs):
        parts=split_ops(ops)
        if mn=='mov' and len(parts)==2:
            dst,src=parts; dr,sr=reg(dst),reg(src)
            if not in_loop(i,intervals):
                di=mem_info(dst)
                if di and 'ebp' not in di[1] and 'esp' not in di[1] and sr and sr in last_load:
                    li,la,ls=last_load[sr]
                    if not in_loop(li,intervals) and i-li<=8:
                        hits.append({'i':i,'store_site':f'0x{addr:08x}','load_site':f'0x{la:08x}','source':ls,'destination':dst,'destination_info':di,'carrier':sr})
            if dr:
                if '[' in src and ']' in src: last_load[dr]=(i,addr,src)
                else: last_load.pop(dr,None)
            continue
        if parts and mn in WRITE_MNEMONICS:
            r=reg(parts[0])
            if r: last_load.pop(r,None)
        if mn.startswith('call'):
            for r in ('eax','ecx','edx'): last_load.pop(r,None)
    return hits


def contiguous_coverage(hits):
    ranges=[]
    for h in hits:
        w,_base,off,_expr=h['destination_info']
        if w is None: return False,0
        ranges.append((off,off+w))
    ranges.sort(); s,e=ranges[0]; best=0
    for ns,ne in ranges[1:]:
        if ns<=e: e=max(e,ne)
        else: best=max(best,e-s); s,e=ns,ne
    best=max(best,e-s)
    return best>=8,best


def clusters(instrs):
    bybase=collections.defaultdict(list)
    for h in transfer_hits(instrs): bybase[h['destination_info'][1]].append(h)
    result=[]
    for base,hs in bybase.items():
        comp=[]
        for h in hs:
            if not comp or h['i']-comp[-1]['i']<=16: comp.append(h)
            else:
                if len(comp)>=2:
                    ok,cov=contiguous_coverage(comp)
                    if ok: result.append((base,comp,cov))
                comp=[h]
        if len(comp)>=2:
            ok,cov=contiguous_coverage(comp)
            if ok: result.append((base,comp,cov))
    return result


def analyze(database: Path, executable: Path, max_depth=4):
    db=sqlite3.connect(database)
    try:
        fmt=index_format(db); adj,sites=direct_graph(db,fmt); reachable,paths=reachability(adj,max_depth); ranges=sized_ranges(db,reachable)
    finally: db.close()
    inst=parse_instructions(disassemble(executable),ranges)
    cands=[]
    for start,_end,name,depth in ranges:
        cls=clusters(inst.get(name,[]))
        if not cls: continue
        path=paths[name]; pedges=[]
        for a,b in zip(path,path[1:]): pedges.append({'from':a,'to':b,'callsites':sorted(set(sites[(a,b)]))})
        rows=[]
        for base,hs,cov in cls:
            rows.append({'destination_base':base,'contiguous_coverage_bytes':cov,'store_count':len(hs),'transfers':[{k:v for k,v in h.items() if k not in ('i','destination_info')} for h in hs]})
        cands.append({'function':name,'address':f'0x{start:08x}','min_direct_depth':depth,'shortest_path':path,'path_edges':pedges,'clusters':rows})
    cands.sort(key=lambda r:(r['min_direct_depth'],r['address'],r['function']))
    return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','scope':'slot0/slot1 shallow straight-line unrolled ordinary-MOV copy navigation frontier','source_index_format':fmt,'source_index_sha256':sha256_file(database),'retail_executable_sha256':sha256_file(executable),'roots':list(ROOTS),'max_direct_call_depth':max_depth,'reachable_unique_node_count':len(reachable),'reachable_sized_function_count':len(ranges),'candidate_function_count':len(cands),'candidates':cands,'adjudication':{'navigation_frontier_captured':True,'zero_init_included':False,'loop_body_transfers_included':False,'candidate_reachability_proves_selected_hdvehicle_alias':False,'unrolled_copy_semantics_complete':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'next_step':'Adjudicate the 11 bounded candidates by exact receiver/destination provenance, then inventory straight-line zero-init separately before deeper/indirect expansion.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('database',type=Path); ap.add_argument('executable',type=Path); ap.add_argument('--max-depth',type=int,default=4); ap.add_argument('--output',type=Path); a=ap.parse_args()
    p=analyze(a.database,a.executable,a.max_depth); text=json.dumps(p,indent=2,sort_keys=True)+'\n'
    a.output.write_text(text,encoding='utf-8') if a.output else print(text,end='')
    return 0
if __name__=='__main__': raise SystemExit(main())
