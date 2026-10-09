#!/usr/bin/env python3
"""Bound canonical non-REP x86 MOVS/STOS paths for P1.3A slot0/slot1.

This follows the REP closure with the canonical bare string-op encodings A4/A5,
AA/AB and their operand-size forms 66 A5/66 AB. SSE MOVSD and ordinary MOV
instructions are deliberately outside this bounded subset. Ghidra callgraph
reachability is navigation only; PC retail bytes adjudicate destinations.
"""
from __future__ import annotations
import argparse,bisect,collections,hashlib,json,re,sqlite3,subprocess,struct
from pathlib import Path

FORMAT="SHIFT.P1A.P13ASlot01BareStringFrontier/1"
SUPPORTED_INDEXES={"SHIFT.GhidraSQLiteIndex/1","SHIFT.GhidraSQLiteIndex/2"}
RETAIL_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INDEX_SHA256="ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
DEFAULT_ROOTS=("FUN_00758b50","FUN_0076d100","FUN_00763570","FUN_00770e80")
BARE_STRING_BYTES={"a4","a5","aa","ab","66a5","66ab"}
EXPECTED_BYTES={
  0x006343DC:"bf309bbf00",0x00634415:"befcbeae00",0x0063441A:"f3a5",0x0063441C:"66a5",
  0x0063442F:"bee0beae00",0x00634434:"f3a5",0x00634436:"a4",
  0x007710B2:"e8d3211900",0x0090328A:"bad06bb900",0x0090328F:"e96cd50000",0x00910827:"e89e000000",
  0x009109C8:"8d7508",0x009109CB:"8dbd7affffff",0x009109D1:"a5",0x009109D2:"a5",
  0x009109D9:"8d7510",0x009109DC:"8d7d82",0x009109DF:"a5",0x009109E0:"a5",
}
EXPECTED_REL32_TARGETS={0x007710B2:0x0090328A,0x0090328F:0x00910800,0x00910827:0x009108CA}
LINE_RE=re.compile(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(\S+)(.*)$")

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def index_format(db):
 row=db.execute("select value from metadata where key='format'").fetchone()
 if not row: raise ValueError('SQLite index has no metadata format')
 fmt=str(row[0])
 if fmt not in SUPPORTED_INDEXES: raise ValueError(f'unsupported SQLite index format: {fmt!r}')
 return fmt

def function_ranges(db):
 out=[]
 for a,n,rj in db.execute('select address,name,raw_json from functions'):
  try: st=int(str(a),16); sz=int(json.loads(rj).get('size') or 0)
  except (ValueError,TypeError,json.JSONDecodeError): continue
  if st>0 and sz>0 and n: out.append((st,st+sz,str(n)))
 out.sort(); return out

def direct_graph(db,fmt):
 g=collections.defaultdict(list)
 if fmt=="SHIFT.GhidraSQLiteIndex/1":
  for (rj,) in db.execute('select raw_json from calls'):
   rec=json.loads(rj)
   if rec.get('indirect'): continue
   s=str(rec.get('from_name') or rec.get('from_function') or '')
   d=str(rec.get('to_name') or rec.get('to') or '')
   site=str(rec.get('instruction') or rec.get('callsite') or '')
   if s and d:g[s].append((d,site))
 else:
  for s,d,site,kind,ind in db.execute('select caller,callee,callsite,kind,indirect from calls'):
   if ind or str(kind).lower()=='indirect':continue
   if s and d:g[str(s)].append((str(d),str(site or '')))
 return g

def parse_bare_string_sites(text:str)->list[dict]:
 out=[]
 for line in text.splitlines():
  m=LINE_RE.match(line)
  if not m: continue
  encoded=''.join(m.group(2).split()).lower()
  if encoded not in BARE_STRING_BYTES: continue
  addr=int(m.group(1),16)
  out.append({'address_int':addr,'address':f'0x{addr:08x}','bytes':encoded,'mnemonic':m.group(3).lower(),'text':line.strip()})
 return out

def map_sites(sites,ranges):
 starts=[x[0] for x in ranges]; out=[]
 for s in sites:
  a=s['address_int']; i=bisect.bisect_right(starts,a)-1; x=dict(s);x.pop('address_int');x['function']=None
  if i>=0 and ranges[i][0]<=a<ranges[i][1]:x['function']=ranges[i][2]
  out.append(x)
 return out

def bfs(g,root,max_depth):
 d={root:0};p={};ps={};q=collections.deque([root])
 while q:
  x=q.popleft()
  if d[x]>=max_depth:continue
  for y,site in g.get(x,[]):
   if y in d:continue
   d[y]=d[x]+1;p[y]=x;ps[y]=site;q.append(y)
 return d,p,ps

def path_to(root,node,d,p,ps):
 nodes=[node];sites=[];cur=node
 while cur!=root:
  sites.append(ps[cur]);cur=p[cur];nodes.append(cur)
 return {'depth':d[node],'nodes':list(reversed(nodes)),'callsites':list(reversed(sites))}

def pe_layout(data:bytes):
 pe=struct.unpack_from('<I',data,0x3c)[0]
 if data[:2]!=b'MZ' or data[pe:pe+4]!=b'PE\0\0':raise ValueError('invalid PE image')
 coff=pe+4; n=struct.unpack_from('<H',data,coff+2)[0]; optsz=struct.unpack_from('<H',data,coff+16)[0];opt=coff+20
 if struct.unpack_from('<H',data,opt)[0]!=0x10b:raise ValueError('expected PE32')
 base=struct.unpack_from('<I',data,opt+28)[0];table=opt+optsz;secs=[]
 for i in range(n):
  off=table+i*40;vs,va,rs,rp=struct.unpack_from('<IIII',data,off+8);secs.append((va,max(vs,rs),rp))
 return base,secs

def va_bytes(data,va,size):
 base,secs=pe_layout(data);rva=va-base
 for srva,span,rp in secs:
  if srva<=rva<srva+span:return data[rp+rva-srva:rp+rva-srva+size]
 raise ValueError(f'unmapped VA {va:#x}')

def verify_anchors(exe:Path):
 data=exe.read_bytes();wins=[];rels=[]
 for va,hx in EXPECTED_BYTES.items():
  exp=bytes.fromhex(hx);got=va_bytes(data,va,len(exp))
  if got!=exp:raise ValueError(f'anchor mismatch {va:#x}: {got.hex()} != {hx}')
  wins.append({'address':f'0x{va:08x}','bytes':hx})
 for va,target in EXPECTED_REL32_TARGETS.items():
  raw=va_bytes(data,va,5)
  if raw[0] not in (0xe8,0xe9):raise ValueError(f'expected rel32 transfer at {va:#x}')
  got=va+5+int.from_bytes(raw[1:],'little',signed=True)
  if got!=target:raise ValueError(f'target mismatch {va:#x}: {got:#x} != {target:#x}')
  rels.append({'site':f'0x{va:08x}','target':f'0x{target:08x}'})
 return {'byte_windows':wins,'rel32_transfers':rels}

def analyze(exe:Path,dbpath:Path,max_depth=4,objdump='objdump'):
 eh=sha256(exe);dh=sha256(dbpath)
 if eh!=RETAIL_SHA256:raise ValueError(f'unexpected retail SHA-256: {eh}')
 if dh!=INDEX_SHA256:raise ValueError(f'unexpected SQLite SHA-256: {dh}')
 db=sqlite3.connect(dbpath)
 try:fmt=index_format(db);ranges=function_ranges(db);g=direct_graph(db,fmt)
 finally:db.close()
 anchors=verify_anchors(exe)
 text=subprocess.run([objdump,'-d','-M','intel',str(exe)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
 allsites=parse_bare_string_sites(text);mapped=map_sites(allsites,ranges);mapped=[x for x in mapped if x['function']]
 by=collections.defaultdict(list)
 for s in mapped:by[s['function']].append(s)
 cpaths=collections.defaultdict(list); roots=[]
 for root in DEFAULT_ROOTS:
  d,p,ps=bfs(g,root,max_depth);hits=[]
  for fn in sorted(by):
   if fn not in d:continue
   path=path_to(root,fn,d,p,ps);hits.append({'function':fn,'path':path,'sites':by[fn]});cpaths[fn].append({'root':root,**path})
  hits.sort(key=lambda h:(h['path']['depth'],h['function']));roots.append({'root':root,'hits':hits})
 cand=[]
 for fn,paths in cpaths.items():cand.append({'function':fn,'minimum_depth':min(x['depth'] for x in paths),'reachable_from':sorted(paths,key=lambda x:(x['depth'],x['root'])),'sites':by[fn]})
 cand.sort(key=lambda x:(x['minimum_depth'],x['function']))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':eh,'source_index_format':fmt,'source_index_sha256':dh,'machine_transfer_adjudicates':True,'callgraph_is_navigation_only':True},'max_direct_call_depth':max_depth,'roots':list(DEFAULT_ROOTS),'whole_image_canonical_bare_string_site_count':len(allsites),'mapped_bare_string_site_count':len(mapped),'mapped_bare_string_function_count':len(by),'distinct_shallow_candidate_count':len(cand),'verified_machine_anchors':anchors,'root_results':roots,'shallow_candidates':cand,'adjudication':{'navigation_frontier_captured':True,'shallow_bare_string_candidates_semantically_rejected':False,'slot0_selected_root_alias_callee_bulk_copy_complete':False,'slot1_selected_root_alias_callee_bulk_copy_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('database',type=Path);ap.add_argument('--max-depth',type=int,default=4);ap.add_argument('--objdump',default='objdump');ap.add_argument('--output',type=Path);a=ap.parse_args()
 try:p=analyze(a.executable,a.database,a.max_depth,a.objdump)
 except (ValueError,subprocess.CalledProcessError) as e:ap.error(str(e))
 text=json.dumps(p,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(text)
 else:print(text,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())
