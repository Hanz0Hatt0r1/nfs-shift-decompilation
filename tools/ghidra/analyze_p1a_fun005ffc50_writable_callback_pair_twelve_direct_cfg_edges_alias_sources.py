#!/usr/bin/env python3
"""Bound up to twelve resolved direct-CFG-edge exact aliases of callback slots 0x00b87b7c/0x00b87b80."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairTwelveDirectCfgEdgesAliasSources/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairEightDirectCfgEdgesAliasSources/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGETS={0x00b87b80,0x00b87b7c};REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$');MEM=re.compile(r'\[([^\]]+)\]');IMM=re.compile(r'^(?:0x([0-9a-fA-F]+)|([0-9]+))$');DIRECT=re.compile(r'^(?:0x)?([0-9a-fA-F]+)(?:\s|$)')
READ_ONLY_FIRST={'cmp','test','push','call','jmp','bt','btc','btr','bts','nop'};CONTROL={'int','int3','ud2','iret','iretd'};MAX_DEPTH=12
EXPECTED_SEEDS={'1':35329,'2':39184,'3':47455,'4':58362,'5':72068,'6':88419,'7':105925,'8':125644,'9':148181,'10':171180,'11':195549,'12':221237}
EXPECTED_STATES={'1':34890,'2':36265,'3':42307,'4':50536,'5':60521,'6':72035,'7':83429,'8':97087,'9':110979,'10':126067,'11':141772,'12':158354}
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
def eval_expr(expr,c):
 total=0;used=False
 for raw in terms(expr):
  sign=-1 if raw.startswith('-') else 1;t=raw[1:] if raw[:1] in '+-' else raw
  if '*' in t:
   r,sc=t.split('*',1)
   if r not in c:return None
   n=imm(sc)
   if n is None:return None
   total+=sign*c[r]*n;used=True
  elif t in REGS:
   if t not in c:return None
   total+=sign*c[t];used=True
  else:
   n=imm(t)
   if n is None:return None
   total+=sign*n
 return total&0xffffffff if used else None
def writes_reg(mn,ops,r):
 p=ops.split(',') if ops else []
 if mn=='xchg' and any(x==r or SUB.get(x)==r for x in p):return True
 if p and mn not in READ_ONLY_FIRST and (p[0]==r or SUB.get(p[0])==r):return True
 if r in {'eax','edx'} and mn in {'mul','div','idiv','cdq','cwd','cwde'}:return True
 if r in {'eax','edx'} and mn=='imul' and len(p)==1:return True
 return False
def update(mn,ops,c):
 p=ops.split(',') if ops else [];c=dict(c)
 if mn=='call':return {r:v for r,v in c.items() if r in {'ebx','esi','edi','ebp'}}
 if mn in {'jmp','ret','retn'} or mn.startswith('j') or mn.startswith('loop') or mn in CONTROL:return {}
 if mn=='mov' and len(p)==2 and p[0] in REGS:
  d,s=p;n=imm(s)
  if n is not None:c[d]=n&0xffffffff
  elif s in c:c[d]=c[s]
  else:c.pop(d,None)
 elif mn=='lea' and len(p)==2 and p[0] in REGS:
  d,s=p;m=MEM.fullmatch(s);v=eval_expr(m.group(1),c) if m else None
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
def scan(rows,max_depth=MAX_DEPTH):
 rows=list(rows);index={a:i for i,(a,_,__) in enumerate(rows)};c={};queue=[];raw=Counter()
 for i,(a,mn,ops) in enumerate(rows):
  before=dict(c)
  if mn=='jmp' or mn.startswith('j'):
   q=DIRECT.match(ops)
   if q and before:
    target=int(q.group(1),16)
    if target in index:queue.append((index[target],tuple(sorted(before.items())),1));raw[1]+=1
    if mn!='jmp' and i+1<len(rows):queue.append((i+1,tuple(sorted(before.items())),1));raw[1]+=1
  c=update(mn,ops,c)
 seen=set();forms=[];uses=[];by_depth=Counter();max_steps=0;pos=0
 while pos<len(queue):
  ii,state_tuple,depth=queue[pos];pos+=1;key=(ii,state_tuple,depth)
  if key in seen:continue
  seen.add(key);by_depth[depth]+=1;c=dict(state_tuple);j=ii;steps=0
  while j<len(rows):
   a,mn,ops=rows[j];before=dict(c);steps+=1;max_steps=max(max_steps,steps)
   for q in MEM.finditer(ops):
    expr=q.group(1)
    if not any(re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',expr) for r in REGS):continue
    ea=eval_expr(expr,before)
    if ea in TARGETS:uses.append({'depth':depth,'site':f'0x{a:08x}','effective_address':f'0x{ea:08x}'})
   after=update(mn,ops,c)
   for r,v in after.items():
    if v in TARGETS and before.get(r)!=v:forms.append({'depth':depth,'site':f'0x{a:08x}','register':r,'value':f'0x{v:08x}'})
   if mn=='jmp' or mn.startswith('j'):
    if depth<max_depth:
     q=DIRECT.match(ops)
     if q and c:
      nd=depth+1;target=int(q.group(1),16)
      if target in index:queue.append((index[target],tuple(sorted(c.items())),nd));raw[nd]+=1
      if mn!='jmp' and j+1<len(rows):queue.append((j+1,tuple(sorted(c.items())),nd));raw[nd]+=1
    break
   if mn.startswith('loop') or mn in {'ret','retn'}|CONTROL:break
   c=after
   if not c:break
   j+=1
 return {'decoded_instruction_count':len(rows),'successor_seed_count_by_depth':{str(k):v for k,v in sorted(raw.items())},'unique_exact_state_count_by_depth':{str(k):v for k,v in sorted(by_depth.items())},'unique_exact_state_count':len(seen),'maximum_successor_region_instruction_count':max_steps,'computed_exact_slot_register_formation_count':len(forms),'computed_exact_slot_memory_operand_count':len(uses),'computed_exact_slot_register_formations':forms,'computed_exact_slot_memory_operands':uses}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_up_to_eight_direct_cfg_edges_computed_alias_source_subset_complete'):raise AssertionError('upstream incomplete')
 r=scan(dis(exe))
 if r['decoded_instruction_count']!=2847850 or r['successor_seed_count_by_depth']!=EXPECTED_SEEDS or r['unique_exact_state_count_by_depth']!=EXPECTED_STATES or r['unique_exact_state_count']!=1014242 or r['maximum_successor_region_instruction_count']!=1224 or r['computed_exact_slot_register_formation_count'] or r['computed_exact_slot_memory_operand_count']:raise AssertionError(('twelve-edge alias drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'targets':['0x00b87b80','0x00b87b7c'],'constant_model':'upstream exact GPR model carried through at most twelve resolved direct JMP/Jcc successor edges','state_key':'instruction index + exact incoming GPR constant state + edge depth'},'inventory':r,'adjudication':{'p13a_fun005ffc50_writable_callback_pair_up_to_twelve_direct_cfg_edges_computed_alias_source_subset_complete':True,'writable_callback_pair_up_to_twelve_direct_cfg_edges_computed_exact_alias_found':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This proves exact computed callback-slot aliases only through at most twelve resolved direct CFG edges.','A cycle-aware fixed point is not claimed; deeper paths, joins, stack/heap aliases, nonconstant address construction and runtime mutation remain open.'],'next_step':'Introduce target-relevance pruning or a sound may-state widening before deeper/fixed-point callback-slot propagation, then classify nonconstant/runtime alias mutation.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
