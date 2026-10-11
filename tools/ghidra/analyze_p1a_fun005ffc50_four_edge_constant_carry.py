#!/usr/bin/env python3
"""Bound path-sensitive exact-GPR constant carry through up to four direct CFG edges for FUN_005ffc50."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from collections import Counter,deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50FourEdgeConstantCarry/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50OneEdgeConstantCarry/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET=0x005ffc50; MASK=0xffffffff; MAX_EDGES=4
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
IMM=re.compile(r'^(?:0x([0-9a-fA-F]+)|(-?\d+))$')
MEM_SIMPLE=re.compile(r'^\[(eax|ebx|ecx|edx|esi|edi|ebp)([+-]0x[0-9a-fA-F]+)?\]$')
MEM_SCALE=re.compile(r'^\[(eax|ebx|ecx|edx|esi|edi|ebp)\*([1248])([+-]0x[0-9a-fA-F]+)?\]$')
WRITE={'mov','lea','add','sub','xor','or','and','shl','sal','shr','sar','inc','dec','imul','neg','not','movzx','movsx','pop'}
STOP={'ret','retn','iret','iretd','int','int3','ud2'}
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def imm(s):
 m=IMM.match(s.strip())
 if not m:return None
 return (int(m.group(1),16) if m.group(1) is not None else int(m.group(2)))&MASK
def memexpr(s,c):
 m=MEM_SIMPLE.match(s)
 if m:
  r,d=m.groups()
  if r not in c:return None
  dd=int(d,16) if d and d[0]=='+' else (-int(d[1:],16) if d else 0)
  return (c[r]+dd)&MASK
 m=MEM_SCALE.match(s)
 if m:
  r,sc,d=m.groups()
  if r not in c:return None
  dd=int(d,16) if d and d[0]=='+' else (-int(d[1:],16) if d else 0)
  return (c[r]*int(sc)+dd)&MASK
 return None
def dest(mn,op):
 if mn not in WRITE:return None
 d=op.split(',',1)[0].strip();return d if d in REGS else SUB.get(d)
def apply(mn,op,c):
 p=[x.strip() for x in op.split(',')] if op else []
 if mn=='xchg' and len(p)==2 and p[0] in REGS and p[1] in REGS:
  a,b=p;av=c.get(a);bv=c.get(b)
  if bv is None:c.pop(a,None)
  else:c[a]=bv
  if av is None:c.pop(b,None)
  else:c[b]=av
  return
 if mn=='mov' and len(p)==2 and p[0] in REGS:
  d,s=p;v=imm(s);v=c.get(s) if v is None and s in REGS else v
  if v is None:c.pop(d,None)
  else:c[d]=v
  return
 if mn=='lea' and len(p)==2 and p[0] in REGS:
  d,s=p;v=memexpr(s,c)
  if v is None:c.pop(d,None)
  else:c[d]=v
  return
 if mn in {'add','sub','xor','or','and'} and len(p)==2 and p[0] in REGS:
  d,s=p;old=c.get(d);k=imm(s);k=c.get(s) if k is None and s in REGS else k
  if s==d and mn in {'xor','sub'}:c[d]=0;return
  if old is None or k is None:c.pop(d,None);return
  c[d]=({'add':old+k,'sub':old-k,'xor':old^k,'or':old|k,'and':old&k}[mn])&MASK;return
 if mn in {'shl','sal','shr','sar'} and len(p)==2 and p[0] in REGS:
  d,s=p;v=c.get(d);k=imm(s)
  if v is None or k is None:c.pop(d,None);return
  k&=31
  if mn in {'shl','sal'}:v=(v<<k)&MASK
  elif mn=='shr':v>>=k
  else:v=((v if v<0x80000000 else v-0x100000000)>>k)&MASK
  c[d]=v;return
 if mn in {'inc','dec','neg','not'} and len(p)==1 and p[0] in REGS:
  d=p[0];v=c.get(d)
  if v is None:c.pop(d,None);return
  c[d]=({'inc':v+1,'dec':v-1,'neg':-v,'not':~v}[mn])&MASK;return
 if mn=='imul' and len(p)==3 and p[0] in REGS and p[1] in REGS:
  d,s,k=p;v=c.get(s);kk=imm(k)
  if v is None or kk is None:c.pop(d,None)
  else:c[d]=(v*kk)&MASK
  return
 d=dest(mn,op)
 if d:c.pop(d,None)
 if mn in {'mul','div','idiv','cdq','cwd','cwde'}:c.pop('eax',None);c.pop('edx',None)
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True);out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def dt(op):
 try:return int(op,16)
 except:return None
def initial_seeds(rows):
 idx={a:i for i,(a,_,_) in enumerate(rows)};c={};seeds=[];same=[]
 for i,(a,mn,op) in enumerate(rows):
  if mn=='call':c.clear();continue
  if mn=='jmp':
   t=dt(op)
   if c and t in idx:seeds.append((a,mn,t,None,dict(c)))
   c.clear();continue
  if mn.startswith('j') or mn.startswith('loop'):
   t=dt(op);ft=rows[i+1][0] if i+1<len(rows) else None
   if c and t in idx:seeds.append((a,mn,t,ft,dict(c)))
   c.clear();continue
  if mn in STOP:c.clear();continue
  before={r for r,v in c.items() if v==TARGET};apply(mn,op,c)
  for r,v in c.items():
   if v==TARGET and r not in before:same.append((a,r))
 if same:raise AssertionError(('same-block target unexpectedly found',same))
 return idx,seeds
def scan(rows):
 idx,seeds=initial_seeds(rows)
 q=deque(); initial_paths=0
 for ba,bmn,t,ft,state in seeds:
  for sk,start in [('target',t),('fallthrough',ft)]:
   if start is not None and start in idx:
    initial_paths+=1;q.append((ba,bmn,sk,start,state,1,[start]))
 seen={};mats=[];xf=[];path_evals=0;sim=0;max_block=0;edge_depth=Counter();max_queue=0
 while q:
  max_queue=max(max_queue,len(q));ba,bmn,sk,start,state,depth,trace=q.popleft()
  key=(start,tuple(sorted(state.items())))
  rem=MAX_EDGES-depth
  if seen.get(key,-1)>=rem:continue
  seen[key]=rem;path_evals+=1;edge_depth[depth]+=1
  cs=dict(state);j=idx[start];l=0
  while j+l<len(rows):
   a,mn,op=rows[j+l];l+=1;sim+=1
   if mn=='call':
    if op in REGS and cs.get(op)==TARGET:xf.append({'seed_branch':f'0x{ba:08x}','depth':depth,'site':f'0x{a:08x}','kind':'call','register':op,'trace':[f'0x{x:08x}' for x in trace]})
    break
   if mn=='jmp':
    if op in REGS and cs.get(op)==TARGET:xf.append({'seed_branch':f'0x{ba:08x}','depth':depth,'site':f'0x{a:08x}','kind':'jmp','register':op,'trace':[f'0x{x:08x}' for x in trace]})
    t=dt(op)
    if depth<MAX_EDGES and cs and t in idx:q.append((ba,bmn,'target',t,dict(cs),depth+1,trace+[t]))
    break
   if mn.startswith('j') or mn.startswith('loop'):
    t=dt(op);ft=rows[j+l][0] if j+l<len(rows) else None
    if depth<MAX_EDGES and cs:
     if t in idx:q.append((ba,bmn,'target',t,dict(cs),depth+1,trace+[t]))
     if ft in idx:q.append((ba,bmn,'fallthrough',ft,dict(cs),depth+1,trace+[ft]))
    break
   if mn in STOP:break
   before={r for r,v in cs.items() if v==TARGET};apply(mn,op,cs)
   for r,v in cs.items():
    if v==TARGET and r not in before:mats.append({'seed_branch':f'0x{ba:08x}','depth':depth,'site':f'0x{a:08x}','register':r,'instruction':f'{mn} {op}'.rstrip(),'trace':[f'0x{x:08x}' for x in trace]})
  max_block=max(max_block,l)
 return {'branch_seed_count':len(seeds),'initial_successor_path_count':initial_paths,'max_edges':MAX_EDGES,'evaluated_state_block_count':path_evals,'evaluated_state_block_count_by_depth':{str(k):edge_depth[k] for k in sorted(edge_depth)},'simulated_instruction_count':sim,'max_scanned_block_instruction_count':max_block,'unique_start_state_count':len(seen),'max_work_queue_depth':max_queue,'materializations':mats,'indirect_transfers':xf}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 a=up.get('adjudication',{})
 if not a.get('p13a_fun005ffc50_one_direct_cfg_edge_constant_carry_subset_complete'):raise AssertionError('upstream one-edge subset incomplete')
 rows=dis(exe);r=scan(rows)
 if r['materializations'] or r['indirect_transfers']:raise AssertionError(('four-edge reconstruction positive',r))
 if len(rows)!=2847850 or r['branch_seed_count']!=17745 or r['initial_successor_path_count']!=30181:raise AssertionError(('inventory drift',len(rows),r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'target':'FUN_005ffc50','target_address':'0x005ffc50','decoded_instruction_count':len(rows),'path_model':'path-sensitive exact GPR constants carried through up to four direct conditional/unconditional CFG edges','max_direct_cfg_edges':MAX_EDGES,'calls_clear_and_terminate_carried_state':True,'indirect_branch_successors_not_followed':True},'inventory':r,'adjudication':{'p13a_fun005ffc50_up_to_four_direct_cfg_edge_constant_carry_subset_complete':True,'four_edge_fun005ffc50_materialization_found':False,'four_edge_fun005ffc50_indirect_transfer_found':False,'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,'return_value_fun005ffc50_provenance_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'encoded_or_reconstructed_callback_entry_ruled_out':False,'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'fun0067b660_callback_argument_provenance_complete':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This extends the one-edge exact-constant subset through at most four direct CFG edges while keeping taken and fallthrough states path-separated.','Calls terminate carried state; return values, memory-backed values, indirect-branch successors, and paths requiring five or more direct edges remain open.','This is not an unbounded phi/fixed-point proof and does not merge alternative predecessor states.','No global reconstructed-entry, callback, writable-runtime, stored-alias, slot0, slot1 or aggregate P1.3 gate is promoted.'],'next_step':'Trace five-plus-edge/phi, return-value and writable/runtime-memory provenance to FUN_005ffc50; direct/static through four direct CFG edges is now separately bounded.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
