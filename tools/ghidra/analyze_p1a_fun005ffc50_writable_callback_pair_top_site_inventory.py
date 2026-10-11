#!/usr/bin/env python3
"""Classify the static TOP memory-use frontier emitted by the callback-slot may-state widening pass."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re
from collections import Counter,defaultdict,deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairTopSiteInventory/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairMayStateWideningFrontier/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
EXPECTED_SITE_CLASSES={'single_top_only':2686,'mixed_single_top_and_finite_overflow':90,'contains_two_top':15,'finite_combination_overflow_only':2}
EXPECTED_TOP_REG_SITES={'eax':701,'ebp':21,'ebx':320,'ecx':352,'edi':550,'edx':111,'esi':751}
EXPECTED_MNEMONICS={'add':7,'and':5,'cmp':465,'fadd':8,'fcom':7,'fcomp':3,'fdiv':1,'fld':158,'fmul':5,'fst':51,'fstp':171,'fsub':12,'fsubr':3,'jmp':9,'lea':630,'lock':1,'mov':1160,'movs':2,'movsx':1,'movzx':59,'or':3,'push':5,'rep':4,'sub':1,'test':19,'xor':3}
def load_model():
 p=Path(__file__).with_name('analyze_p1a_fun005ffc50_writable_callback_pair_may_state_widening_frontier.py')
 s=importlib.util.spec_from_file_location('p1a_cb_widen_model',p);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def scan_frontier(rows,model):
 rows=list(rows);index={a:i for i,(a,_,__) in enumerate(rows)}
 seed_by_idx={};c={}
 for i,(a,mn,ops) in enumerate(rows):
  before=dict(c)
  if mn=='jmp' or mn.startswith('j'):
   q=model.DIRECT.match(ops)
   if q and before:
    t=int(q.group(1),16);succ=[]
    if t in index:succ.append(index[t])
    if mn!='jmp' and i+1<len(rows):succ.append(i+1)
    for si in succ:seed_by_idx[si]=model.merge_state(seed_by_idx.get(si,{}),model.lift_exact(before))
  c=model.exact_update(mn,ops,c)
 state_by_idx=dict(seed_by_idx);q=deque(seed_by_idx);obs=defaultdict(list)
 while q:
  ii=q.popleft();c=dict(state_by_idx[ii]);j=ii
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
     old=state_by_idx.get(si,{})
     merged=model.merge_state(old,c)
     if merged!=old:state_by_idx[si]=merged;q.append(si)
    break
   if mn.startswith('loop') or mn in {'ret','retn'}|model.CONTROL:break
   c=after
   if not c:break
   j+=1
 site_classes=Counter();top_reg_sites=Counter();mnemonics=Counter();expressions=Counter();samples=[];observation_count=0
 for a,items in sorted(obs.items()):
  observation_count+=len(items);counts=[len(x[2]) for x in items]
  if max(counts)==0:cls='finite_combination_overflow_only'
  elif max(counts)>=2:cls='contains_two_top'
  elif min(counts)==1:cls='single_top_only'
  else:cls='mixed_single_top_and_finite_overflow'
  site_classes[cls]+=1
  site_regs=set(r for _,_,rs in items for r in rs)
  for r in site_regs:top_reg_sites[r]+=1
  site_mn={x[0] for x in items};site_expr={x[1] for x in items}
  for mn in site_mn:mnemonics[mn]+=1
  for expr in site_expr:expressions[expr]+=1
  if len(samples)<64:samples.append({'site':f'0x{a:08x}','class':cls,'top_registers':sorted(site_regs),'mnemonics':sorted(site_mn),'memory_expressions':sorted(site_expr)})
 return {'decoded_instruction_count':len(rows),'top_memory_use_site_count':len(obs),'top_memory_use_observation_count':observation_count,'unique_memory_expression_count':len(expressions),'site_class_counts':dict(sorted(site_classes.items())),'top_register_site_counts':dict(sorted(top_reg_sites.items())),'site_mnemonic_counts':dict(sorted(mnemonics.items())),'top_expression_samples':[{'expression':e,'site_count':n} for e,n in expressions.most_common(64)],'site_samples':samples}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_may_state_widening_frontier_subset_complete'):raise AssertionError('upstream incomplete')
 if up['inventory'].get('top_memory_use_site_count')!=2793:raise AssertionError('upstream frontier drift')
 model=load_model();r=scan_frontier(model.dis(exe),model)
 expected=(2847850,2793,6401,893)
 got=(r['decoded_instruction_count'],r['top_memory_use_site_count'],r['top_memory_use_observation_count'],r['unique_memory_expression_count'])
 if got!=expected or r['site_class_counts']!=EXPECTED_SITE_CLASSES or r['top_register_site_counts']!=EXPECTED_TOP_REG_SITES or r['site_mnemonic_counts']!=EXPECTED_MNEMONICS:raise AssertionError(('top-site inventory drift',got,r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'frontier':'all 2,793 static TOP memory-use sites from the may-state widening contract','site_classification':'distinguishes direct TOP-register dependence from finite candidate cross-product overflow','deduplication':'site counts are static instruction addresses; observation count retains repeated abstract-state visits'},'inventory':r,'adjudication':{'p13a_fun005ffc50_writable_callback_pair_top_site_inventory_subset_complete':True,'writable_callback_pair_top_site_frontier_classified':True,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This inventories and partitions the existing TOP frontier; it does not prove any TOP site irrelevant to either callback slot.','A modular-arithmetic reachability experiment eliminated zero static sites when TOP was interpreted as any 32-bit value, so provenance must be retained to refine this frontier soundly.'],'next_step':'Refine the 2,686 single-TOP-only sites with provenance-preserving widened value classes before attempting mixed/two-TOP sites.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
