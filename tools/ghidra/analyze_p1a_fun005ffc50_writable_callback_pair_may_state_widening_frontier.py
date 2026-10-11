#!/usr/bin/env python3
"""Compute a finite may-state widening frontier for callback-slot exact-constant aliases."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from collections import Counter,deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairMayStateWideningFrontier/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairTwelveDirectCfgEdgesAliasSources/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGETS={0x00b87b80,0x00b87b7c};REG_ORDER=('eax','ebx','ecx','edx','esi','edi','ebp');REGS=set(REG_ORDER);CAP=8;TOP=object()
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$');MEM=re.compile(r'\[([^\]]+)\]');IMM=re.compile(r'^(?:0x([0-9a-fA-F]+)|([0-9]+))$');DIRECT=re.compile(r'^(?:0x)?([0-9a-fA-F]+)(?:\s|$)')
READ_ONLY_FIRST={'cmp','test','push','call','jmp','bt','btc','btr','bts','nop'};CONTROL={'int','int3','ud2','iret','iretd'}
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout
 for line in p.stdout:
  m=I.match(line)
  if m:yield int(m.group(1),16),m.group(2).lower(),norm(m.group(3))
 err=p.stderr.read() if p.stderr else ''
 if p.wait():raise RuntimeError(err)
def imm(s):
 m=IMM.fullmatch(s)
 if not m:return None
 return int(m.group(1),16) if m.group(1) else int(m.group(2))
def terms(expr):return re.findall(r'[+-]?[^+-]+',expr.replace(' ',''))
def writes_reg(mn,ops,r):
 p=ops.split(',') if ops else []
 if mn=='xchg' and any(x==r or SUB.get(x)==r for x in p):return True
 if p and mn not in READ_ONLY_FIRST and (p[0]==r or SUB.get(p[0])==r):return True
 if r in {'eax','edx'} and mn in {'mul','div','idiv','cdq','cwd','cwde'}:return True
 if r in {'eax','edx'} and mn=='imul' and len(p)==1:return True
 return False
def exact_eval(expr,c):
 total=0;used=False
 for raw in terms(expr):
  sign=-1 if raw.startswith('-') else 1;t=raw[1:] if raw[:1] in '+-' else raw
  if '*' in t:
   r,sc=t.split('*',1);n=imm(sc)
   if r not in c or n is None:return None
   total+=sign*c[r]*n;used=True
  elif t in REGS:
   if t not in c:return None
   total+=sign*c[t];used=True
  else:
   n=imm(t)
   if n is None:return None
   total+=sign*n
 return total&0xffffffff if used else None
def exact_update(mn,ops,c):
 p=ops.split(',') if ops else [];c=dict(c)
 if mn=='call':return {r:v for r,v in c.items() if r in {'ebx','esi','edi','ebp'}}
 if mn in {'jmp','ret','retn'} or mn.startswith('j') or mn.startswith('loop') or mn in CONTROL:return {}
 if mn=='mov' and len(p)==2 and p[0] in REGS:
  d,s=p;n=imm(s)
  if n is not None:c[d]=n&0xffffffff
  elif s in c:c[d]=c[s]
  else:c.pop(d,None)
 elif mn=='lea' and len(p)==2 and p[0] in REGS:
  d,s=p;m=MEM.fullmatch(s);v=exact_eval(m.group(1),c) if m else None
  if v is None:c.pop(d,None)
  else:c[d]=v
 elif mn in {'add','sub'} and len(p)==2 and p[0] in REGS:
  d,s=p;n=imm(s)
  if d in c and n is not None:c[d]=(c[d]+(n if mn=='add' else -n))&0xffffffff
  else:c.pop(d,None)
 elif mn=='xor' and len(p)==2 and p[0] in REGS and p[0]==p[1]:c[p[0]]=0
 else:
  for r in REGS:
   if writes_reg(mn,ops,r):c.pop(r,None)
 return c
def one(v):return frozenset((v&0xffffffff,))
def merge_val(a,b):
 if a is TOP or b is TOP:return TOP
 if a is None:return b
 if b is None:return a
 u=a|b
 return TOP if len(u)>CAP else u
def merge_state(a,b):
 out={}
 for r in REG_ORDER:
  v=merge_val(a.get(r),b.get(r))
  if v is not None:out[r]=v
 return out
def lift_exact(c):return {r:one(v) for r,v in c.items()}
def vals_apply(v,fn):
 if v is TOP:return TOP
 if v is None:return None
 out=frozenset(fn(x)&0xffffffff for x in v)
 return TOP if len(out)>CAP else out
def combine(a,b,fn):
 if a is TOP or b is TOP:return TOP
 if a is None or b is None:return None
 if len(a)*len(b)>CAP:return TOP
 out=set()
 for x in a:
  for y in b:
   out.add(fn(x,y)&0xffffffff)
   if len(out)>CAP:return TOP
 return frozenset(out)
def eval_abs(expr,c):
 acc=one(0);used=False
 for raw in terms(expr):
  sign=-1 if raw.startswith('-') else 1;t=raw[1:] if raw[:1] in '+-' else raw
  if '*' in t:
   r,sc=t.split('*',1);n=imm(sc)
   if r not in REGS or n is None:return None
   v=c.get(r)
   if v is None:return None
   acc=combine(acc,vals_apply(v,lambda x:x*n*sign),lambda x,y:x+y);used=True
  elif t in REGS:
   v=c.get(t)
   if v is None:return None
   acc=combine(acc,vals_apply(v,lambda x:x*sign),lambda x,y:x+y);used=True
  else:
   n=imm(t)
   if n is None:return None
   acc=vals_apply(acc,lambda x:x+sign*n)
  if acc is TOP:return TOP
 return acc if used else None
def abs_update(mn,ops,c):
 p=ops.split(',') if ops else [];c=dict(c)
 if mn=='call':return {r:v for r,v in c.items() if r in {'ebx','esi','edi','ebp'}}
 if mn=='mov' and len(p)==2 and p[0] in REGS:
  d,s=p;n=imm(s)
  if n is not None:c[d]=one(n)
  elif s in REGS:
   if s in c:c[d]=c[s]
   else:c.pop(d,None)
  else:c.pop(d,None)
 elif mn=='lea' and len(p)==2 and p[0] in REGS:
  d,s=p;m=MEM.fullmatch(s);v=eval_abs(m.group(1),c) if m else None
  if v is None:c.pop(d,None)
  else:c[d]=v
 elif mn in {'add','sub'} and len(p)==2 and p[0] in REGS:
  d,s=p;n=imm(s)
  if d in c and n is not None:c[d]=vals_apply(c[d],lambda x:x+(n if mn=='add' else -n))
  else:c.pop(d,None)
 elif mn=='xor' and len(p)==2 and p[0] in REGS and p[0]==p[1]:c[p[0]]=one(0)
 else:
  for r in list(c):
   if writes_reg(mn,ops,r):c.pop(r,None)
 return c
def has_target(v):return v is not None and v is not TOP and bool(TARGETS & set(v))
def scan(rows):
 rows=list(rows);index={a:i for i,(a,_,__) in enumerate(rows)}
 seed_by_idx={};c={};seed_edges=0
 for i,(a,mn,ops) in enumerate(rows):
  before=dict(c)
  if mn=='jmp' or mn.startswith('j'):
   q=DIRECT.match(ops)
   if q and before:
    target=int(q.group(1),16);succ=[]
    if target in index:succ.append(index[target])
    if mn!='jmp' and i+1<len(rows):succ.append(i+1)
    for si in succ:
     seed_edges+=1;seed_by_idx[si]=merge_state(seed_by_idx.get(si,{}),lift_exact(before))
  c=exact_update(mn,ops,c)
 state_by_idx=dict(seed_by_idx);q=deque(seed_by_idx);updates=Counter();top_forms=set();top_uses=set();exact_hits=set();processed=0
 while q:
  ii=q.popleft();processed+=1;c=dict(state_by_idx[ii]);j=ii
  while j<len(rows):
   a,mn,ops=rows[j];before=dict(c)
   for mq in MEM.finditer(ops):
    expr=mq.group(1)
    if not any(re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',expr) for r in REGS):continue
    v=eval_abs(expr,before)
    if v is TOP:top_uses.add(a)
    elif has_target(v):exact_hits.add(('use',a))
   after=abs_update(mn,ops,c)
   for r,v in after.items():
    if v is TOP and before.get(r) is not TOP:top_forms.add((a,r))
    elif has_target(v) and before.get(r)!=v:exact_hits.add(('form',a,r))
   if mn=='jmp' or mn.startswith('j'):
    dm=DIRECT.match(ops);succ=[]
    if dm and c:
     t=int(dm.group(1),16)
     if t in index:succ.append(index[t])
     if mn!='jmp' and j+1<len(rows):succ.append(j+1)
    for si in succ:
     old=state_by_idx.get(si,{})
     merged=merge_state(old,c)
     if merged!=old:state_by_idx[si]=merged;q.append(si);updates[si]+=1
    break
   if mn.startswith('loop') or mn in {'ret','retn'}|CONTROL:break
   c=after
   if not c:break
   j+=1
 top_entry_regs=sum(v is TOP for st in state_by_idx.values() for v in st.values())
 return {'decoded_instruction_count':len(rows),'widening_cap_distinct_constants_per_register':CAP,'initial_successor_seed_edge_count':seed_edges,'initial_joined_successor_entry_count':len(seed_by_idx),'joined_cfg_entry_count':len(state_by_idx),'processed_entry_count':processed,'entry_state_update_count':sum(updates.values()),'maximum_updates_for_one_entry':max(updates.values() or [0]),'top_entry_register_count':top_entry_regs,'top_formation_site_count':len(top_forms),'top_memory_use_site_count':len(top_uses),'exact_callback_slot_hit_count':len(exact_hits),'top_formation_samples':[{'site':f'0x{a:08x}','register':r} for a,r in sorted(top_forms)[:64]],'top_memory_use_samples':[f'0x{x:08x}' for x in sorted(top_uses)[:64]],'exact_callback_slot_hits':[str(x) for x in sorted(exact_hits,key=str)]}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_up_to_twelve_direct_cfg_edges_computed_alias_source_subset_complete'):raise AssertionError('upstream incomplete')
 r=scan(dis(exe));expected=(2847850,35329,32592,116695,452675,420083,35,45681,1591,2793,0)
 got=(r['decoded_instruction_count'],r['initial_successor_seed_edge_count'],r['initial_joined_successor_entry_count'],r['joined_cfg_entry_count'],r['processed_entry_count'],r['entry_state_update_count'],r['maximum_updates_for_one_entry'],r['top_entry_register_count'],r['top_formation_site_count'],r['top_memory_use_site_count'],r['exact_callback_slot_hit_count'])
 if got!=expected:raise AssertionError(('may-state widening drift',got,r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'targets':['0x00b87b80','0x00b87b7c'],'seed_model':'all exact branch-local GPR constant states used by the existing callback-slot CFG series','join_model':'per-register union of candidate exact constants; more than eight distinct constants widens to TOP','top_meaning':'candidate exact-constant set widened beyond the retained finite set; TOP is reported, never treated as a negative proof'},'inventory':r,'adjudication':{'p13a_fun005ffc50_writable_callback_pair_may_state_widening_frontier_subset_complete':True,'writable_callback_pair_may_state_exact_slot_hit_found':False,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This is a finite may-state frontier for the exact-constant source class, not global alias closure.','TOP memory uses are unresolved by construction and therefore prevent promotion of multi-edge/global writable-memory gates.','Nonconstant address construction, stack/heap aliases, external/runtime mutation and generated code remain outside this contract.'],'next_step':'Classify the 2,793 TOP memory-use sites by address expression and producer ancestry; split irrelevant widened values from callback-slot-relevant unresolved flows.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
