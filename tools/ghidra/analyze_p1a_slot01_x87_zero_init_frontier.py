#!/usr/bin/env python3
"""Inventory shallow straight-line x87 FLDZ/FST* zero-init ranges for P1.3A."""
from __future__ import annotations
import argparse,bisect,collections,hashlib,json,re,sqlite3,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13ASlot01X87ZeroInitFrontier/1'
SUPPORTED={'SHIFT.GhidraSQLiteIndex/1','SHIFT.GhidraSQLiteIndex/2'}
ROOTS=('FUN_00758b50','FUN_0076d100','FUN_00763570','FUN_00770e80')
INSN_RE=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([^\s]+)\s*(.*)$');TARGET_RE=re.compile(r'0x([0-9a-fA-F]+)');MEM_RE=re.compile(r'(?:(byte|word|dword|qword) ptr )?\[([^\]]+)\]',re.I)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def mem(op):
 m=MEM_RE.search(op.lower())
 if not m:return None
 w={'byte':1,'word':2,'dword':4,'qword':8,None:None}[m.group(1).lower() if m.group(1) else None];expr=m.group(2).replace(' ','');terms=re.findall(r'[+-]?[^+-]+',expr);c=0;nc=[]
 for t in terms:
  sg=-1 if t.startswith('-') else 1;raw=t[1:] if t[:1] in '+-' else t
  if re.fullmatch(r'0x[0-9a-f]+|\d+',raw):c+=sg*int(raw,0)
  else:nc.append(('-' if sg<0 else '')+raw)
 return w,'+'.join(nc).replace('+-','-'),c,expr
def fmt(db):
 r=db.execute("select value from metadata where key='format'").fetchone();v=str(r[0]) if r else ''
 if v not in SUPPORTED:raise ValueError('unsupported/missing index format')
 return v
def graph(db,v):
 adj=collections.defaultdict(list);sites=collections.defaultdict(list)
 if v.endswith('/1'):
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
def reach(adj,depth=4):
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
  z=int(json.loads(raw).get('size') or 0)
  if z>0:s=int(str(a),16);out.append((s,s+z,str(n),reachable[str(n)]))
 return sorted(out)
def disasm(exe):return subprocess.run(['objdump','-d','-M','intel',str(exe)],check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
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
  if mt:
   t=int(mt.group(1),16)
   if t<a:
    j=next((k for k,r in enumerate(rows) if r[0]>=t),None)
    if j is not None:out.append((j,i))
 return out
def inloop(i,iv):return any(a<=i<=b for a,b in iv)
def hits(rows):
 iv=loop_intervals(rows);zero=False;out=[]
 for i,(a,m,o) in enumerate(rows):
  di=mem(o) if m in ('fst','fstp') else None
  if not inloop(i,iv) and zero and di and 'ebp' not in di[1] and 'esp' not in di[1]:out.append({'i':i,'site':f'0x{a:08x}','mnemonic':m,'destination':o,'info':di})
  if m=='fldz':zero=True
  elif m=='fst':pass
  elif m=='fstp':zero=False
  elif m.startswith('f') and m!='fwait':zero=False
  if m.startswith('call'):zero=False
 return out
def coverage(hs):
 rr=[]
 for h in hs:
  w,_b,o,_e=h['info']
  if w is None:return 0
  rr.append((o,o+w))
 rr.sort();s,e=rr[0];best=0
 for ns,ne in rr[1:]:
  if ns<=e:e=max(e,ne)
  else:best=max(best,e-s);s,e=ns,ne
 return max(best,e-s)
def clusters(rows):
 by=collections.defaultdict(list)
 for h in hits(rows):by[h['info'][1]].append(h)
 out=[]
 for base,hs in by.items():
  comp=[]
  for h in hs:
   if not comp or h['i']-comp[-1]['i']<=24:comp.append(h)
   else:
    c=coverage(comp)
    if c>=8:out.append((base,comp,c))
    comp=[h]
  c=coverage(comp) if comp else 0
  if c>=8:out.append((base,comp,c))
 return out
def analyze(database:Path,executable:Path,max_depth=4):
 db=sqlite3.connect(database)
 try:v=fmt(db);adj,sites=graph(db,v);reachable,paths=reach(adj,max_depth);rs=ranges(db,reachable)
 finally:db.close()
 ins=parse(disasm(executable),rs);c=[]
 for start,_e,n,d in rs:
  cs=clusters(ins.get(n,[]))
  if not cs:continue
  p=paths[n];edges=[{'from':a,'to':b,'callsites':sorted(set(sites[a,b]))} for a,b in zip(p,p[1:])]
  cr=[]
  for base,hs,cov in cs:cr.append({'destination_base':base,'contiguous_coverage_bytes':cov,'store_count':len(hs),'stores':[{k:v for k,v in h.items() if k not in ('i','info')} for h in hs]})
  c.append({'function':n,'address':f'0x{start:08x}','min_direct_depth':d,'shortest_path':p,'path_edges':edges,'clusters':cr})
 c.sort(key=lambda x:(x['min_direct_depth'],x['address'],x['function']))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','scope':'slot0/slot1 shallow x87 FLDZ/FST zero-init navigation frontier','source_index_format':v,'source_index_sha256':sha(database),'retail_executable_sha256':sha(executable),'max_direct_call_depth':max_depth,'reachable_unique_node_count':len(reachable),'reachable_sized_function_count':len(rs),'candidate_function_count':len(c),'candidates':c,'adjudication':{'navigation_frontier_captured':True,'x87_zero_init_semantics_complete':False,'sse_vector_copy_init_complete':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7}}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('database',type=Path);ap.add_argument('executable',type=Path);ap.add_argument('--max-depth',type=int,default=4);ap.add_argument('--output',type=Path);a=ap.parse_args();p=analyze(a.database,a.executable,a.max_depth);t=json.dumps(p,indent=2,sort_keys=True)+'\n';a.output.write_text(t) if a.output else print(t,end='');return 0
if __name__=='__main__':raise SystemExit(main())
