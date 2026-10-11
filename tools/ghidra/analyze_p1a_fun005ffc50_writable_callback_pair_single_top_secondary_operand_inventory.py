#!/usr/bin/env python3
"""Inventory missing secondary GPR operands inside the callback single-TOP frontier."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re
from collections import Counter,defaultdict,deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairSingleTopSecondaryOperandInventory/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairSingleTopCongruenceRefinement/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
EXPECTED_MISSING={'eax':293,'ebp':37,'ebx':81,'ecx':232,'edi':81,'edx':265,'esi':106}
EXPECTED_TOP={'eax':262,'ebx':217,'ecx':87,'edi':311,'edx':15,'esi':203}
EXPECTED_MN={'add':2,'cmp':272,'fadd':6,'fdiv':1,'fld':53,'fst':29,'fstp':50,'fsub':7,'fsubr':2,'lea':152,'mov':474,'movzx':35,'or':2,'push':3,'test':7}
def load_model():
 p=Path(__file__).with_name('analyze_p1a_fun005ffc50_writable_callback_pair_may_state_widening_frontier.py')
 s=importlib.util.spec_from_file_location('p1a_cb_widen_model',p);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def expr_regs(expr,model):
 return set(re.findall(r'(?<![a-z0-9])('+'|'.join(sorted(model.REGS))+r')(?![a-z0-9])',expr))
def classify_site(items,model):
 arity=max(len(expr_regs(x['expr'],model)) for x in items)
 if arity!=2:return {'arity':arity,'secondary_absent':False,'top_registers':set(),'missing_registers':set()}
 tops=set();missing=set()
 for x in items:
  for r in expr_regs(x['expr'],model):
   v=x['state'].get(r)
   if v is model.TOP:tops.add(r)
   elif v is None:missing.add(r)
 return {'arity':arity,'secondary_absent':bool(missing),'top_registers':tops,'missing_registers':missing}
def collect(rows,model):
 rows=list(rows);index={a:i for i,(a,_,__) in enumerate(rows)};seed={};c={}
 for i,(a,mn,ops) in enumerate(rows):
  before=dict(c)
  if mn=='jmp' or mn.startswith('j'):
   q=model.DIRECT.match(ops)
   if q and before:
    t=int(q.group(1),16);succ=[]
    if t in index:succ.append(index[t])
    if mn!='jmp' and i+1<len(rows):succ.append(i+1)
    for si in succ:seed[si]=model.merge_state(seed.get(si,{}),model.lift_exact(before))
  c=model.exact_update(mn,ops,c)
 state=dict(seed);q=deque(seed);obs=defaultdict(list)
 while q:
  ii=q.popleft();c=dict(state[ii]);j=ii
  while j<len(rows):
   a,mn,ops=rows[j];before=dict(c)
   for mq in model.MEM.finditer(ops):
    expr=mq.group(1);regs=expr_regs(expr,model)
    if not regs:continue
    v=model.eval_abs(expr,before)
    if v is model.TOP:
     tops=tuple(sorted(r for r in regs if before.get(r) is model.TOP))
     obs[a].append({'mnemonic':mn,'expr':expr,'tops':tops,'state':{r:before.get(r) for r in regs}})
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
 single={a:items for a,items in obs.items() if max(len(x['tops']) for x in items)==1 and min(len(x['tops']) for x in items)==1}
 arity=Counter();missing=[];represented=[]
 for a,items in single.items():
  cl=classify_site(items,model);arity[cl['arity']]+=1
  if cl['arity']==2:(missing if cl['secondary_absent'] else represented).append((a,items,cl))
 miss=Counter();tops=Counter();pairs=Counter();mns=Counter();exprs=Counter();observations=0;samples=[]
 for a,items,cl in sorted(missing):
  observations+=len(items)
  for r in cl['missing_registers']:miss[r]+=1
  for r in cl['top_registers']:tops[r]+=1
  for t in cl['top_registers']:
   for r in cl['missing_registers']:pairs[f'{t}->{r}']+=1
  for mn in {x['mnemonic'] for x in items}:mns[mn]+=1
  for ex in {x['expr'] for x in items}:exprs[ex]+=1
  if len(samples)<32:samples.append({'site':f'0x{a:08x}','top_registers':sorted(cl['top_registers']),'missing_secondary_registers':sorted(cl['missing_registers']),'mnemonics':sorted({x['mnemonic'] for x in items}),'expressions':sorted({x['expr'] for x in items})})
 return {'decoded_instruction_count':len(rows),'single_top_site_count':len(single),'expression_arity_site_counts':{str(k):v for k,v in sorted(arity.items())},'two_gpr_site_count':len(missing)+len(represented),'two_gpr_secondary_absent_site_count':len(missing),'two_gpr_secondary_fully_represented_site_count':len(represented),'secondary_absent_observation_count':observations,'missing_secondary_register_site_counts':dict(sorted(miss.items())),'top_register_site_counts':dict(sorted(tops.items())),'top_to_missing_secondary_pair_site_counts':dict(sorted(pairs.items())),'mnemonic_site_counts':dict(sorted(mns.items())),'unique_expression_count':len(exprs),'top_expressions':[{'expression':e,'site_count':n} for e,n in exprs.most_common(32)],'secondary_absent_site_samples':samples,'fully_represented_two_gpr_sites':[f'0x{a:08x}' for a,_,__ in sorted(represented)]}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_single_top_congruence_refinement_subset_complete'):raise AssertionError('upstream incomplete')
 if up['inventory'].get('upstream_single_top_only_site_count')!=2686:raise AssertionError('upstream single-TOP drift')
 model=load_model();r=collect(model.dis(exe),model)
 expected=(2847850,2686,{'1':1564,'2':1122},1122,1095,27,2405)
 got=(r['decoded_instruction_count'],r['single_top_site_count'],r['expression_arity_site_counts'],r['two_gpr_site_count'],r['two_gpr_secondary_absent_site_count'],r['two_gpr_secondary_fully_represented_site_count'],r['secondary_absent_observation_count'])
 if got!=expected or r['missing_secondary_register_site_counts']!=EXPECTED_MISSING or r['top_register_site_counts']!=EXPECTED_TOP or r['mnemonic_site_counts']!=EXPECTED_MN:raise AssertionError(('secondary operand inventory drift',got,r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'frontier':'2,686 upstream single-TOP-only static memory-use sites','classification':'count GPR operands in each memory expression and identify two-GPR sites where at least one non-TOP operand is absent from at least one original may-state observation','state_semantics':'uses the pre-congruence finite-set/TOP fixed-point states so this contract inventories a source of precision loss; it does not claim the missing runtime value is unconstrained'},'inventory':r,'adjudication':{'p13a_fun005ffc50_writable_callback_pair_single_top_secondary_operand_inventory_subset_complete':True,'writable_callback_pair_single_top_two_gpr_secondary_absence_classified':True,'writable_callback_pair_single_top_secondary_operand_frontier_empty':False,'writable_callback_pair_single_top_frontier_empty':False,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This inventory identifies a concrete precision-loss source; it does not prove any of the 1,095 sites irrelevant to either callback slot.','The 27 two-GPR sites with fully represented secondary operands remain a separate refinement class.','Congruence-compatible one-GPR sites, mixed/two-TOP classes, stack/heap aliases, runtime mutation and generated code remain open.'],'next_step':'Track the missing secondary operand at the 1,095 two-GPR sites with a dedicated bounded value/provenance domain; separately refine the 27 fully represented two-GPR sites.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
