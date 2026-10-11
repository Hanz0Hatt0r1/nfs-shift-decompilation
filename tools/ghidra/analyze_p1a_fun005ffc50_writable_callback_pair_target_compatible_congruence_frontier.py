#!/usr/bin/env python3
"""Inventory congruence strength of the 15 target-compatible folded-secondary callback sites."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re
from collections import Counter,defaultdict,deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairTargetCompatibleCongruenceFrontier/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairFullyRepresentedSecondaryCongruenceFold/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
EXPECTED={'0 mod 1':7,'0 mod 4':5,'0 mod 8':2,'4 mod 8':1}
def load_fold():
 p=Path(__file__).with_name('analyze_p1a_fun005ffc50_writable_callback_pair_fully_represented_secondary_congruence_fold.py')
 s=importlib.util.spec_from_file_location('p1a_cb_fold',p);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def terminal_class(v,c):
 if c.is_congruence(v):return f'{v[1]} mod {v[2]}'
 if isinstance(v,frozenset):return f'finite:{len(v)}'
 return 'unknown'
def scan(rows,fold,targets):
 c=fold.load_congruence();m=c.load_model();rows=list(rows);wanted={int(x,16) for x in targets};index,seed=c.initial_seeds(rows,m,lambda a,b:c.join_state(a,b,m.REG_ORDER));state=dict(seed);q=deque(seed);seen=defaultdict(list);updates=0
 while q:
  ii=q.popleft();st=dict(state[ii]);j=ii
  while j<len(rows):
   a,mn,ops=rows[j]
   if a in wanted:
    for mq in m.MEM.finditer(ops):
     expr=mq.group(1)
     if any(re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',expr) for r in m.REGS):
      v=c.eval_value(expr,st,m);seen[a].append((mn,expr,v))
   after=c.abstract_update(mn,ops,st,m)
   if mn=='jmp' or mn.startswith('j'):
    dm=m.DIRECT.match(ops);succ=[]
    if dm and st:
     t=int(dm.group(1),16)
     if t in index:succ.append(index[t])
     if mn!='jmp' and j+1<len(rows):succ.append(j+1)
    for si in succ:
     old=state.get(si,{});merged=c.join_state(old,st,m.REG_ORDER)
     if merged!=old:state[si]=merged;q.append(si);updates+=1
    break
   if mn.startswith('loop') or mn in {'ret','retn'}|m.CONTROL:break
   st=after
   if not st:break
   j+=1
 classes=Counter();mn=Counter();samples=[]
 for a in sorted(wanted):
  items=seen[a];term=items[-1][2] if items else None;cl=terminal_class(term,c);classes[cl]+=1
  if items:mn[items[-1][0]]+=1
  samples.append({'site':f'0x{a:08x}','terminal_class':cl,'observation_count':len(items),'mnemonic':items[-1][0] if items else None,'expression':items[-1][1] if items else None})
 return {'decoded_instruction_count':len(rows),'fixed_point_entry_count':len(state),'fixed_point_entry_update_count':updates,'target_compatible_site_count':len(wanted),'terminal_congruence_class_counts':dict(sorted(classes.items())),'terminal_mnemonic_counts':dict(sorted(mn.items())),'sites':samples}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_fully_represented_secondary_congruence_fold_subset_complete'):raise AssertionError('upstream incomplete')
 targets=up['inventory'].get('target_possible_sites',[])
 if len(targets)!=15:raise AssertionError('upstream target-compatible drift')
 f=load_fold();r=scan(f.load_congruence().load_model().dis(exe),f,targets)
 if (r['decoded_instruction_count'],r['fixed_point_entry_count'],r['fixed_point_entry_update_count'])!=(2847850,116677,420030):raise AssertionError(('fixed point drift',r))
 if r['terminal_congruence_class_counts']!=EXPECTED or r['terminal_mnemonic_counts']!={'cmp':7,'lea':3,'mov':5}:raise AssertionError(('frontier drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'frontier':'15 folded-secondary sites still congruence-compatible with at least one callback target','classification':'terminal abstract-address congruence after the sound fixed point stabilizes','purpose':'separate arithmetic precision from provenance precision before deeper refinement'},'inventory':r,'adjudication':{'p13a_fun005ffc50_writable_callback_pair_target_compatible_congruence_frontier_subset_complete':True,'writable_callback_pair_target_compatible_frontier_requires_provenance_refinement':True,'writable_callback_pair_fully_represented_two_gpr_frontier_empty':False,'writable_callback_pair_single_top_frontier_empty':False,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['Seven sites have terminal modulus 1, so congruence arithmetic contains no exclusion information there.','The remaining eight retain modulo-4/8 structure but remain compatible with at least one target.','This contract inventories precision only; it does not rule out any of the 15 sites.'],'next_step':'Trace widening/join provenance for the primary register at the 15 sites, prioritizing the seven modulus-1 sites.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
