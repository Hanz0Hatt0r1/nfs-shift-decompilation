#!/usr/bin/env python3
"""Bound shallow receiver-relative ordinary MOV/FST loop writes for P1.3A.

This is a deliberately bounded custom-init/copy frontier after REP and bare
string-op closures. It finds direct-call reachable functions that preserve
entry ECX in ESI/EDI/EBX and then write through that receiver alias inside a
machine-level backward-jump loop. Callgraph reachability is navigation only;
retail bytes and exact receiver provenance adjudicate the candidates.
"""
from __future__ import annotations
import argparse,bisect,collections,hashlib,json,re,sqlite3,subprocess,struct
from pathlib import Path

FORMAT="SHIFT.P1A.P13ASlot01ReceiverLoopWriteFrontier/1"
SUPPORTED_INDEXES={"SHIFT.GhidraSQLiteIndex/1","SHIFT.GhidraSQLiteIndex/2"}
RETAIL_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
INDEX_SHA256="ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e"
DEFAULT_ROOTS=("FUN_00758b50","FUN_0076d100","FUN_00763570","FUN_00770e80")
EXPECTED_CANDIDATES=(
 "FUN_00765c40","FUN_0075bf60","FUN_007b0710","FUN_006333f0",
 "FUN_007b0600","FUN_00a62780","FUN_00638020","FUN_0076f030",
)
LINE_RE=re.compile(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s*(\S+)(.*)$")
BRANCH_RE=re.compile(r"^(?:0x)?([0-9a-fA-F]+)")

EXPECTED_BYTES={
 0x00765c5f:"8bf1",0x0075bf6b:"8bf1",0x0075bf8d:"888c06ea000000",
 0x00770eab:"e8c0eaffff",0x0076f97d:"8bf1",0x0076f97f:"e8dcc5feff",
 0x00765e38:"8d8d20ffffff",0x00765e4a:"8d55d8",0x00765e86:"e885a80400",
 0x007b0719:"8bf9",0x007b0c50:"897730",0x007b0cb9:"b9e0b9c100",
 0x007b0cbe:"e83df9ffff",0x007b060b:"8bf1",0x007b06ac:"c70600000000",
 0x00765ed8:"8d8e30670000",0x00765ee6:"e855ca2f00",0x00a62947:"8bf9",
 0x00a62b17:"8bcf",0x00a62b19:"e862fcffff",0x00a62789:"8bf9",0x00a627d1:"c7474000000000",
 0x00770105:"e886fdf9ff",0x0077010a:"8bb888020000",0x00770135:"8bcf",0x0077013a:"e861d5ffff",
 0x0076d6bd:"8bf1",0x0076d741:"8bce",0x0076d748:"e8a35cecff",0x006333f7:"8bf1",0x006334f3:"8986b8000000",
 0x0076e75e:"e82d17faff",0x0076e763:"8bb888020000",0x0076e772:"8bcf",0x0076e774:"e817c4f9ff",
 0x0070abf9:"e89286f2ff",0x006332c5:"e8667e0200",0x006332ca:"8b405c",0x006332d4:"8bc8",0x006332d6:"e8454d0000",
 0x00638028:"8bf1",0x00638096:"c70600000000",
 0x00770a25:"8bce",0x00770a27:"e804e6ffff",0x0076f03a:"8bf1",0x0076f0fd:"899ee03f0000",0x0076f265:"899ee03f0000",
}
EXPECTED_REL32_TARGETS={
 0x00770eab:0x0076f970,0x0076f97f:0x0075bf60,0x00765e86:0x007b0710,0x007b0cbe:0x007b0600,
 0x00765ee6:0x00a62940,0x00a62b19:0x00a62780,0x00770105:0x0070fe90,0x0077013a:0x0076d6a0,
 0x0076d748:0x006333f0,0x0076e75e:0x0070fe90,0x0076e774:0x0070ab90,0x0070abf9:0x00633290,
 0x006332c5:0x0065b130,0x006332d6:0x00638020,0x00770a27:0x0076f030,
}

def sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def index_format(db):
 row=db.execute("select value from metadata where key='format'").fetchone()
 if not row:raise ValueError('SQLite index has no metadata format')
 fmt=str(row[0])
 if fmt not in SUPPORTED_INDEXES:raise ValueError(f'unsupported SQLite index format: {fmt!r}')
 return fmt

def function_ranges(db):
 out=[]
 for a,n,rj in db.execute('select address,name,raw_json from functions'):
  try:st=int(str(a),16);sz=int(json.loads(rj).get('size') or 0)
  except (ValueError,TypeError,json.JSONDecodeError):continue
  if st>0 and sz>0 and n:out.append((st,st+sz,str(n)))
 out.sort();return out

def direct_graph(db,fmt):
 g=collections.defaultdict(list)
 if fmt=="SHIFT.GhidraSQLiteIndex/1":
  for (rj,) in db.execute('select raw_json from calls'):
   rec=json.loads(rj)
   if rec.get('indirect'):continue
   s=str(rec.get('from_name') or rec.get('from_function') or '')
   d=str(rec.get('to_name') or rec.get('to') or '')
   site=str(rec.get('instruction') or rec.get('callsite') or '')
   if s and d:g[s].append((d,site))
 else:
  for s,d,site,kind,ind in db.execute('select caller,callee,callsite,kind,indirect from calls'):
   if ind or str(kind).lower()=='indirect':continue
   if s and d:g[str(s)].append((str(d),str(site or '')))
 return g

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
 coff=pe+4;n=struct.unpack_from('<H',data,coff+2)[0];optsz=struct.unpack_from('<H',data,coff+16)[0];opt=coff+20
 base=struct.unpack_from('<I',data,opt+28)[0]; table=opt+optsz; secs=[]
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

def parse_instructions(text,ranges,reachable):
 starts=[x[0] for x in ranges];out=collections.defaultdict(list)
 for line in text.splitlines():
  m=LINE_RE.match(line)
  if not m:continue
  a=int(m.group(1),16);i=bisect.bisect_right(starts,a)-1
  if i<0:continue
  st,en,fn=ranges[i]
  if not(st<=a<en) or fn not in reachable:continue
  out[fn].append((a,m.group(3).lower(),m.group(4).strip(),line.strip()))
 return out

def receiver_loop_candidates(ins_by,depths):
 rows=[]
 for fn,arr in ins_by.items():
  aliases=set()
  for _,mn,op,_ in arr[:40]:
   compact=op.replace(' ','').lower()
   if mn=='mov' and compact in ('esi,ecx','edi,ecx','ebx,ecx'):aliases.add(compact.split(',')[0])
  if not aliases:continue
  idx={a:i for i,(a,*_) in enumerate(arr)};loops=[]
  for j,(a,mn,op,_) in enumerate(arr):
   if not mn.startswith('j'):continue
   mm=BRANCH_RE.match(op)
   if not mm:continue
   target=int(mm.group(1),16)
   if target>=a or target not in idx:continue
   stores=[]
   for aa,mmn,o,ll in arr[idx[target]:j+1]:
    if not (mmn.startswith('mov') or mmn in ('fst','fstp')):continue
    if any(re.match(r'^(?:BYTE PTR |WORD PTR |DWORD PTR |QWORD PTR )?\[[^\]]*\b'+al+r'\b[^\]]*\]\s*,',o,re.I) for al in aliases):
     stores.append({'address':f'0x{aa:08x}','text':ll})
   if stores:loops.append({'start':f'0x{target:08x}','backedge':f'0x{a:08x}','stores':stores})
  if loops:rows.append({'function':fn,'minimum_depth':depths[fn],'receiver_aliases':sorted(aliases),'loops':loops})
 rows.sort(key=lambda x:(x['minimum_depth'],x['function']))
 return rows

def analyze(exe:Path,dbpath:Path,max_depth=4,objdump='objdump'):
 eh=sha256(exe);dh=sha256(dbpath)
 if eh!=RETAIL_SHA256:raise ValueError(f'unexpected retail SHA-256: {eh}')
 if dh!=INDEX_SHA256:raise ValueError(f'unexpected SQLite SHA-256: {dh}')
 db=sqlite3.connect(dbpath)
 try:fmt=index_format(db);ranges=function_ranges(db);g=direct_graph(db,fmt)
 finally:db.close()
 depths={};paths=collections.defaultdict(list)
 for root in DEFAULT_ROOTS:
  d,p,ps=bfs(g,root,max_depth)
  for fn,dep in d.items():
   if fn not in depths or dep<depths[fn]:depths[fn]=dep
   paths[fn].append({'root':root,**path_to(root,fn,d,p,ps)})
 text=subprocess.run([objdump,'-d','-M','intel',str(exe)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
 ins=parse_instructions(text,ranges,set(depths));cands=receiver_loop_candidates(ins,depths)
 names=tuple(x['function'] for x in cands)
 if set(names)!=set(EXPECTED_CANDIDATES) or len(names)!=len(EXPECTED_CANDIDATES):
  raise ValueError(f'unexpected receiver-loop candidate set: {names!r}')
 for c in cands:c['reachable_from']=sorted(paths[c['function']],key=lambda x:(x['depth'],x['root']))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':eh,'source_index_format':fmt,'source_index_sha256':dh,'machine_transfer_adjudicates':True,'callgraph_is_navigation_only':True},'max_direct_call_depth':max_depth,'roots':list(DEFAULT_ROOTS),'candidate_count':len(cands),'candidate_functions':list(names),'candidates':cands,'verified_machine_anchors':verify_anchors(exe),'adjudication':{'navigation_frontier_captured':True,'receiver_loop_candidates_semantically_rejected':False,'slot0_selected_root_alias_callee_bulk_copy_complete':False,'slot1_selected_root_alias_callee_bulk_copy_complete':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('database',type=Path);ap.add_argument('--max-depth',type=int,default=4);ap.add_argument('--objdump',default='objdump');ap.add_argument('--output',type=Path);a=ap.parse_args()
 try:p=analyze(a.executable,a.database,a.max_depth,a.objdump)
 except (ValueError,subprocess.CalledProcessError) as e:ap.error(str(e))
 text=json.dumps(p,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(text,encoding='utf-8')
 else:print(text,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())