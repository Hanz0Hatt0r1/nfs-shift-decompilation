#!/usr/bin/env python3
"""Refine single-TOP callback-slot memory uses with a sound 32-bit congruence domain."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,re
from collections import Counter,defaultdict,deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairSingleTopCongruenceRefinement/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairTopSiteInventory/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
MOD=1<<32;CAP=8
EXPECTED_CLASSES={'congruence_rules_out_target':290,'target_still_possible':1145,'unknown_value':1244,'unseen_in_refined_fixed_point':7}

def load_model():
 p=Path(__file__).with_name('analyze_p1a_fun005ffc50_writable_callback_pair_may_state_widening_frontier.py')
 s=importlib.util.spec_from_file_location('p1a_cb_widen_model',p);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def is_congruence(v):return isinstance(v,tuple) and len(v)==3 and v[0]=='congruence'
def finite_hull(v):
 xs=list(v);r=xs[0];md=MOD
 for x in xs[1:]:md=math.gcd(md,(x-r)%MOD)
 return r%md,md
def from_values(values):
 v=frozenset(x&0xffffffff for x in values)
 if len(v)<=CAP:return v
 r,md=finite_hull(v);return ('congruence',r,md)
def join_value(a,b):
 if a is None:return b
 if b is None:return a
 if not is_congruence(a) and not is_congruence(b):return from_values(set(a)|set(b))
 ra,ma=(a[1],a[2]) if is_congruence(a) else finite_hull(a)
 rb,mb=(b[1],b[2]) if is_congruence(b) else finite_hull(b)
 g=math.gcd(MOD,ma,mb,(rb-ra)%MOD)
 return ('congruence',ra%g,g)
def join_state(a,b,order):
 out={}
 for r in order:
  v=join_value(a.get(r),b.get(r))
  if v is not None:out[r]=v
 return out
def lift_exact(c):return {r:frozenset((v&0xffffffff,)) for r,v in c.items()}
def affine(v,scale=1,add=0):
 if v is None:return None
 if not is_congruence(v):return from_values((scale*x+add for x in v))
 r,md=v[1],v[2];new_md=math.gcd(MOD,abs(scale)*md)
 return ('congruence',(scale*r+add)%new_md,new_md)
def add_values(a,b):
 if a is None or b is None:return None
 if not is_congruence(a) and not is_congruence(b):return from_values((x+y for x in a for y in b))
 ra,ma=(a[1],a[2]) if is_congruence(a) else finite_hull(a)
 rb,mb=(b[1],b[2]) if is_congruence(b) else finite_hull(b)
 g=math.gcd(ma,mb);return ('congruence',(ra+rb)%g,g)
def eval_value(expr,c,model):
 acc=frozenset((0,));used=False
 for raw in model.terms(expr):
  sign=-1 if raw.startswith('-') else 1;t=raw[1:] if raw[:1] in '+-' else raw
  if '*' in t:
   r,sc=t.split('*',1);n=model.imm(sc)
   if r not in model.REGS or n is None or c.get(r) is None:return None
   acc=add_values(acc,affine(c[r],sign*n));used=True
  elif t in model.REGS:
   if c.get(t) is None:return None
   acc=add_values(acc,affine(c[t],sign));used=True
  else:
   n=model.imm(t)
   if n is None:return None
   acc=affine(acc,1,sign*n)
 return acc if used else None
def target_possible(v,targets):
 if v is None:return None
 if is_congruence(v):
  r,md=v[1],v[2];return any(t%md==r for t in targets)
 return bool(set(v)&set(targets))
def abstract_update(mn,ops,c,model):
 p=ops.split(',') if ops else [];c=dict(c)
 if mn=='call':return {r:v for r,v in c.items() if r in {'ebx','esi','edi','ebp'}}
 if mn=='mov' and len(p)==2 and p[0] in model.REGS:
  d,s=p;n=model.imm(s)
  if n is not None:c[d]=frozenset((n&0xffffffff,))
  elif s in model.REGS:
   if s in c:c[d]=c[s]
   else:c.pop(d,None)
  else:c.pop(d,None)
 elif mn=='lea' and len(p)==2 and p[0] in model.REGS:
  d,s=p;mm=model.MEM.fullmatch(s);v=eval_value(mm.group(1),c,model) if mm else None
  if v is None:c.pop(d,None)
  else:c[d]=v
 elif mn in {'add','sub'} and len(p)==2 and p[0] in model.REGS:
  d,s=p;n=model.imm(s)
  if d in c and n is not None:c[d]=affine(c[d],1,n if mn=='add' else -n)
  else:c.pop(d,None)
 elif mn=='xor' and len(p)==2 and p[0] in model.REGS and p[0]==p[1]:c[p[0]]=frozenset((0,))
 else:
  for r in list(c):
   if model.writes_reg(mn,ops,r):c.pop(r,None)
 return c

def initial_seeds(rows,model,join):
 index={a:i for i,(a,_,__) in enumerate(rows)};seed={};c={}
 for i,(a,mn,ops) in enumerate(rows):
  before=dict(c)
  if mn=='jmp' or mn.startswith('j'):
   q=model.DIRECT.match(ops)
   if q and before:
    t=int(q.group(1),16);succ=[]
    if t in index:succ.append(index[t])
    if mn!='jmp' and i+1<len(rows):succ.append(i+1)
    for si in succ:seed[si]=join(seed.get(si,{}),lift_exact(before))
  c=model.exact_update(mn,ops,c)
 return index,seed

def single_top_sites(rows,model):
 index,seed=initial_seeds(rows,model,lambda a,b:model.merge_state(a,b));state=dict(seed);q=deque(seed);obs=defaultdict(list)
 while q:
  ii=q.popleft();c=dict(state[ii]);j=ii
  while j<len(rows):
   a,mn,ops=rows[j];before=dict(c)
   for mq in model.MEM.finditer(ops):
    expr=mq.group(1)
    if not any(re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',expr) for r in model.REGS):continue
    v=model.eval_abs(expr,before)
    if v is model.TOP:
     tops=tuple(sorted(r for r in model.REGS if before.get(r) is model.TOP and re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',expr)))
     obs[a].append((mn,expr,tops))
   after=model.abs_update(mn,ops,c)
   if mn=='jmp' or mn.startswith('j'):
    dm=model.DIRECT.match(ops);succ=[]
    if dm and c:
     t=int(dm.group(1),16)
     if t in index:succ.append(index[t])
     if mn!='jmp' and j+1<len(rows):succ.append(j+1)
    for si in succ:
     old=state.get(si,{});merged=model.merge_state(old,c)
     if merged!=old:state[si]=merged;q.append(si)
    break
   if mn.startswith('loop') or mn in {'ret','retn'}|model.CONTROL:break
   c=after
   if not c:break
   j+=1
 return {a:items for a,items in obs.items() if max(len(x[2]) for x in items)==1 and min(len(x[2]) for x in items)==1}

def scan(rows,model):
 rows=list(rows);sites=single_top_sites(rows,model);join=lambda a,b:join_state(a,b,model.REG_ORDER);index,seed=initial_seeds(rows,model,join)
 state=dict(seed);q=deque(seed);seen=defaultdict(list);updates=0
 while q:
  ii=q.popleft();c=dict(state[ii]);j=ii
  while j<len(rows):
   a,mn,ops=rows[j];before=dict(c)
   if a in sites:
    for mq in model.MEM.finditer(ops):
     expr=mq.group(1)
     if not any(re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',expr) for r in model.REGS):continue
     v=eval_value(expr,before,model);seen[a].append((expr,v,target_possible(v,model.TARGETS)))
   after=abstract_update(mn,ops,c,model)
   if mn=='jmp' or mn.startswith('j'):
    dm=model.DIRECT.match(ops);succ=[]
    if dm and c:
     t=int(dm.group(1),16)
     if t in index:succ.append(index[t])
     if mn!='jmp' and j+1<len(rows):succ.append(j+1)
    for si in succ:
     old=state.get(si,{});merged=join(old,c)
     if merged!=old:state[si]=merged;q.append(si);updates+=1
    break
   if mn.startswith('loop') or mn in {'ret','retn'}|model.CONTROL:break
   c=after
   if not c:break
   j+=1
 classes=Counter();regs=Counter();mnems=Counter();mods=Counter();samples=[];observations=0
 for a,origin in sorted(sites.items()):
  items=seen.get(a,[]);observations+=len(items)
  if not items:cl='unseen_in_refined_fixed_point'
  elif any(p is True for _,_,p in items):cl='target_still_possible'
  elif any(p is None for _,_,p in items):cl='unknown_value'
  elif any(is_congruence(v) for _,v,_ in items):cl='congruence_rules_out_target'
  else:cl='finite_exact_rules_out_target'
  classes[cl]+=1
  if cl=='congruence_rules_out_target':
   for mn,_,tops in origin:
    mnems[mn]+=1
    for r in tops:regs[r]+=1
   for _,v,_ in items:
    if is_congruence(v):mods[v[2]]+=1
   if len(samples)<32:
    samples.append({'site':f'0x{a:08x}','top_registers':sorted({r for _,_,ts in origin for r in ts}),'mnemonics':sorted({mn for mn,_,_ in origin}),'memory_expressions':sorted({expr for expr,_,_ in items}),'congruences':[{'residue':f'0x{v[1]:08x}','modulus':v[2]} for _,v,_ in items if is_congruence(v)][:8]})
 return {'decoded_instruction_count':len(rows),'upstream_single_top_only_site_count':len(sites),'refined_memory_use_observation_count':observations,'refined_cfg_entry_count':len(state),'refined_entry_state_update_count':updates,'refinement_class_counts':dict(sorted(classes.items())),'congruence_excluded_site_count':classes['congruence_rules_out_target'],'unresolved_single_top_site_count':len(sites)-classes['congruence_rules_out_target'],'excluded_top_register_observation_counts':dict(sorted(regs.items())),'excluded_mnemonic_observation_counts':dict(sorted(mnems.items())),'excluded_congruence_modulus_observation_counts':dict(sorted(mods.items())),'excluded_site_samples':samples}

def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_top_site_inventory_subset_complete'):raise AssertionError('upstream incomplete')
 if up['inventory']['site_class_counts'].get('single_top_only')!=2686:raise AssertionError('upstream single-TOP drift')
 model=load_model();r=scan(model.dis(exe),model)
 got=(r['decoded_instruction_count'],r['upstream_single_top_only_site_count'],r['refined_memory_use_observation_count'],r['refined_cfg_entry_count'],r['refined_entry_state_update_count'],r['refinement_class_counts'])
 exp=(2847850,2686,33644,116677,420030,EXPECTED_CLASSES)
 if got!=exp:raise AssertionError(('single-TOP congruence drift',got))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'input_frontier':'2,686 single-TOP-only static memory-use sites from the upstream TOP inventory','domain':'hybrid finite exact set (cap 8) plus sound 32-bit congruence hull after widening','operations_preserved':'MOV copy/immediate, affine LEA, ADD/SUB immediate, XOR self-zeroing; direct CFG fixed point and established callee-saved call policy','exclusion_rule':'a site is excluded only when every refined observation is known and at least one congruence observation exists, while neither callback-slot target satisfies any observed congruence'},'inventory':r,'adjudication':{'p13a_fun005ffc50_writable_callback_pair_single_top_congruence_refinement_subset_complete':True,'writable_callback_pair_single_top_congruence_exclusion_found':True,'writable_callback_pair_single_top_frontier_empty':False,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['Only 290 of the 2,686 single-TOP-only sites are excluded by congruence incompatibility. The remaining 2,396 sites stay unresolved.','1,145 sites remain congruence-compatible with a callback slot, 1,244 require at least one other unrepresented register value, and seven are not observed in the refined fixed point.','Mixed single-TOP/finite-overflow, two-TOP, finite-combination-overflow, nonconstant memory aliases, stack/heap aliases, runtime mutation and generated code remain outside this contract.'],'next_step':'Refine the 1,145 congruence-compatible single-TOP sites with provenance classes; separately resolve the 1,244 expressions containing other unrepresented registers.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
