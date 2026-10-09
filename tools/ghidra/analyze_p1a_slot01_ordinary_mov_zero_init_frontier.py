#!/usr/bin/env python3
"""Inventory shallow straight-line ordinary-MOV zero-init ranges for P1.3A."""
from __future__ import annotations
import argparse,bisect,collections,hashlib,json,re,sqlite3,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13ASlot01OrdinaryMovZeroInitFrontier/1'
SUPPORTED={'SHIFT.GhidraSQLiteIndex/1','SHIFT.GhidraSQLiteIndex/2'}
ROOTS=('FUN_00758b50','FUN_0076d100','FUN_00763570','FUN_00770e80')
REGS={'eax','ebx','ecx','edx','esi','edi','ebp','esp'}
INSN_RE=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([^\s]+)\s*(.*)$')
TARGET_RE=re.compile(r'0x([0-9a-fA-F]+)')
MEM_RE=re.compile(r'(?:(byte|word|dword|qword) ptr )?\[([^\]]+)\]',re.I)
WRITE={'mov','lea','add','sub','inc','dec','xor','and','or','shl','shr','sar','imul'}

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def split(s):return [x.strip() for x in s.split(',',1)] if ',' in s else [s.strip()]
def reg(s):
 v=re.sub(r'^(?:byte|word|dword|qword) ptr\s+','',s.lower().strip());return v if v in REGS else None
def mem(op):
 m=MEM_RE.search(op.lower())
 if not m:return None
 w={'byte':1,'word':2,'dword':4,'qword':8,None:None}[m.group(1).lower() if m.group(1) else None]
 expr=m.group(2).replace(' ','');terms=re.findall(r'[+-]?[^+-]+',expr);c=0;nc=[]
 for t in terms:
  sg=-1 if t.startswith('-') else 1;raw=t[1:] if t[:1] in '+-' else t
  if re.fullmatch(r'0x[0-9a-f]+|\d+',raw):c+=sg*int(raw,0)
  else:nc.append(('-' if sg<0 else '')+raw)
 return w,'+'.join(nc).replace('+-','-'),c,expr
def fmt(db):
 row=db.execute("select value from metadata where key='format'").fetchone()
 if not row or str(row[0]) not in SUPPORTED:raise ValueError('unsupported/missing index format')
 return str(row[0])
def graph(db,version):
 adj=collections.defaultdict(list);sites=collections.defaultdict(list)
 if version.endswith('/1'):
  for (raw,) in db.execute('select raw_json from calls'):
   r=json.loads(raw)
   if r.get('indirect'):continue
   a=str(r.get('from_name') or r.get('from_function') or '');b=str(r.get('to_name') or r.get('to') or '');s=str(r.get('instruction') or r.get('callsite') or '')
   if a and b:adj[a].append(b);sites[a,b].append(s)
 else:
  for a,b,s,k,ind in db.execute('select caller,callee,callsite,kind,indirect from calls'):
   if ind or str(k).lower()=='indirect' or not a or not b:continue
   a,b=str(a),str(b);adj[a].append(b);sites[a,b].append(str(s or ''))
 return adj,sites
def reach(adj,depth):
 best={};paths={}
 for root in ROOTS:
  dist={root:0};par={};q=collections.deque([root])
  while q:
   n=q.popleft()
   if dist[n]>=depth:continue
   for c in adj.get(n,[]):
    if c in dist:continue
    dist[c]=dist[n]+1;par[c]=n;q.append(c)
  for n,d in dist.items():
   if d>=best.get(n,1<<30):continue
   best[n]=d;p=[n];cur=n
   while cur!=root:cur=par[cur];p.append(cur)
   paths[n]=p[::-1]
 return best,paths
def ranges(db,reachable):
 out=[]
 for a,n,raw in db.execute('select address,name,raw_json from functions'):
  if n not in reachable or not a:continue
  size=int(json.loads(raw).get('size') or 0)
  if size>0:s=int(str(a),16);out.append((s,s+size,str(n),reachable[str(n)]))
 return sorted(out)
def disasm(exe):
 return subprocess.run(['objdump','-d','-M','intel',str(exe)],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
def parse(text,rs):
 starts=[x[0] for x in rs];out=collections.defaultdict(list)
 for line in text.splitlines():
  m=INSN_RE.match(line)
  if not m:continue
  a=int(m.group(1),16);i=bisect.bisect_right(starts,a)-1
  if i<0:continue
  s,e,n,_=rs[i]
  if s<=a<e:out[n].append((a,m.group(2).lower(),m.group(3).strip()))
 return out
def loop_intervals(rows):
 out=[]
 for i,(a,m,o) in enumerate(rows):
  if not m.startswith('j'):continue
  mt=TARGET_RE.search(o)
  if not mt:continue
  t=int(mt.group(1),16)
  if t>=a:continue
  j=next((k for k,r in enumerate(rows) if r[0]>=t),None)
  if j is not None:out.append((j,i))
 return out
def inloop(i,ivs):return any(a<=i<=b for a,b in ivs)
def zero_hits(rows):
 iv=loop_intervals(rows);zeros=set();out=[]
 for i,(a,m,o) in enumerate(rows):
  ps=split(o)
  if m=='xor' and len(ps)==2 and reg(ps[0]) and reg(ps[0])==reg(ps[1]):zeros.add(reg(ps[0]));continue
  if m=='mov' and len(ps)==2:
   dst,src=ps;dr,sr=reg(dst),reg(src);di=mem(dst)
   if not inloop(i,iv) and di and 'ebp' not in di[1] and 'esp' not in di[1] and (src.lower() in ('0','0x0') or (sr and sr in zeros)):
    out.append({'i':i,'site':f'0x{a:08x}','destination':dst,'source':src,'info':di})
   if dr:
    if src.lower() in ('0','0x0') or (sr and sr in zeros):zeros.add(dr)
    else:zeros.discard(dr)
   continue
  if ps and m in WRITE:
   r=reg(ps[0])
   if r:zeros.discard(r)
  if m.startswith('call'):zeros.difference_update({'eax','ecx','edx'})
 return out
def coverage(hs):
 rr=[]
 for h in hs:
  w,_base,off,_expr=h['info']
  if w is None:return 0
  rr.append((off,off+w))
 rr.sort();s,e=rr[0];best=0
 for ns,ne in rr[1:]:
  if ns<=e:e=max(e,ne)
  else:best=max(best,e-s);s,e=ns,ne
 return max(best,e-s)
def clusters(rows):
 by=collections.defaultdict(list)
 for h in zero_hits(rows):by[h['info'][1]].append(h)
 out=[]
 for base,hs in by.items():
  comp=[]
  for h in hs:
   if not comp or h['i']-comp[-1]['i']<=20:comp.append(h)
   else:
    c=coverage(comp)
    if len(comp)>=2 and c>=8:out.append((base,comp,c))
    comp=[h]
  c=coverage(comp) if comp else 0
  if len(comp)>=2 and c>=8:out.append((base,comp,c))
 return out
def analyze(database:Path,executable:Path,max_depth=4):
 db=sqlite3.connect(database)
 try:
  version=fmt(db);adj,sites=graph(db,version);reachable,paths=reach(adj,max_depth);rs=ranges(db,reachable)
 finally:db.close()
 ins=parse(disasm(executable),rs);cands=[]
 for start,_end,name,depth in rs:
  cls=clusters(ins.get(name,[]))
  if not cls:continue
  path=paths[name];edges=[]
  for a,b in zip(path,path[1:]):edges.append({'from':a,'to':b,'callsites':sorted(set(sites[a,b]))})
  crow=[]
  for base,hs,cov in cls:
   crow.append({'destination_base':base,'contiguous_coverage_bytes':cov,'store_count':len(hs),'stores':[{k:v for k,v in h.items() if k not in ('i','info')} for h in hs]})
  cands.append({'function':name,'address':f'0x{start:08x}','min_direct_depth':depth,'shortest_path':path,'path_edges':edges,'clusters':crow})
 cands.sort(key=lambda r:(r['min_direct_depth'],r['address'],r['function']))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','scope':'slot0/slot1 shallow straight-line ordinary-MOV zero-init frontier','source_index_format':version,'source_index_sha256':sha(database),'retail_executable_sha256':sha(executable),'max_direct_call_depth':max_depth,'reachable_unique_node_count':len(reachable),'reachable_sized_function_count':len(rs),'candidate_function_count':len(cands),'candidates':cands,'adjudication':{'navigation_frontier_captured':True,'ordinary_mov_zero_init_semantics_complete':False,'x87_zero_init_included':False,'sse_vector_zero_init_included':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7}}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('database',type=Path);ap.add_argument('executable',type=Path);ap.add_argument('--max-depth',type=int,default=4);ap.add_argument('--output',type=Path);a=ap.parse_args();p=analyze(a.database,a.executable,a.max_depth);t=json.dumps(p,indent=2,sort_keys=True)+'\n';a.output.write_text(t) if a.output else print(t,end='');return 0
if __name__=='__main__':raise SystemExit(main())
