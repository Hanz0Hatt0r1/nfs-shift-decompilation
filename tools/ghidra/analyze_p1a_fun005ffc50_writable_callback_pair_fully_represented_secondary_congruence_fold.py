#!/usr/bin/env python3
"""Fold singleton secondary operands and refine the 27-site callback alias frontier by congruence."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re
from collections import Counter,defaultdict,deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairFullyRepresentedSecondaryCongruenceFold/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairFullyRepresentedSecondarySingletons/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
SITES=['0x004b9124','0x00503328','0x0050334b','0x00572951','0x00572957','0x0057295e','0x00572965','0x005d5621','0x006084d0','0x00608539','0x0060853f','0x007a6e9e','0x007a6ea5','0x007f25a0','0x0080b696','0x00878f82','0x00878f88','0x00878f8f','0x00878f96','0x00a64930','0x00a64936','0x00a6493d','0x00a64944','0x00a64e40','0x00a64e46','0x00a64e4d','0x00a64e54']
RULED=['0x00572957','0x0057295e','0x00572965','0x00878f88','0x00878f8f','0x00878f96','0x00a64936','0x00a6493d','0x00a64944','0x00a64e46','0x00a64e4d','0x00a64e54']
def load_congruence():
 p=Path(__file__).with_name('analyze_p1a_fun005ffc50_writable_callback_pair_single_top_congruence_refinement.py');s=importlib.util.spec_from_file_location('p1a_cb_cong',p);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def classify(observations):
 if not observations:return 'unseen'
 if any(x['target_possible'] is True for x in observations):return 'target_possible'
 if any(x['target_possible'] is None for x in observations):return 'unknown'
 return 'ruled_out'
def scan(rows,c):
 m=c.load_model();rows=list(rows);targets={int(x,16) for x in SITES};index,seed=c.initial_seeds(rows,m,lambda a,b:c.join_state(a,b,m.REG_ORDER));state=dict(seed);q=deque(seed);seen=defaultdict(list);updates=0
 while q:
  ii=q.popleft();st=dict(state[ii]);j=ii
  while j<len(rows):
   a,mn,ops=rows[j];before=dict(st)
   if a in targets:
    for mq in m.MEM.finditer(ops):
     expr=mq.group(1)
     if not any(re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',expr) for r in m.REGS):continue
     v=c.eval_value(expr,before,m);p=None if v is None else c.target_possible(v,m.TARGETS)
     seen[a].append({'mnemonic':mn,'expression':expr,'value':v,'target_possible':p})
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
 classes=Counter();ruled=[];possible=[];residue=Counter()
 for a in sorted(targets):
  cl=classify(seen.get(a,[]));classes[cl]+=1;(ruled if cl=='ruled_out' else possible).append(f'0x{a:08x}')
  if cl=='ruled_out':
   for x in seen[a]:
    v=x['value']
    if c.is_congruence(v):residue[f"{v[1]} mod {v[2]}"]+=1
 return {'decoded_instruction_count':len(rows),'fixed_point_entry_count':len(state),'fixed_point_entry_update_count':updates,'folded_secondary_site_count':27,'class_counts':dict(sorted(classes.items())),'ruled_out_site_count':len(ruled),'target_possible_site_count':len(possible),'ruled_out_sites':ruled,'target_possible_sites':possible,'ruled_out_congruence_residue_observation_counts':dict(sorted(residue.items()))}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest();
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('writable_callback_pair_fully_represented_secondary_values_all_singleton'):raise AssertionError('upstream incomplete')
 c=load_congruence();r=scan(c.load_model().dis(exe),c)
 if (r['decoded_instruction_count'],r['fixed_point_entry_count'],r['fixed_point_entry_update_count'])!=(2847850,116677,420030):raise AssertionError(('fixed point drift',r))
 if r['class_counts']!={'ruled_out':12,'target_possible':15} or r['ruled_out_sites']!=RULED:raise AssertionError(('fold result drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'frontier':'27 fully represented two-GPR single-TOP sites from the upstream singleton contract','method':'evaluate the original affine memory expression in the sound finite-set/congruence fixed point; singleton secondary operands are therefore folded exactly','targets':['0x00b87b80','0x00b87b7c']},'inventory':r,'adjudication':{'p13a_fun005ffc50_writable_callback_pair_fully_represented_secondary_congruence_fold_subset_complete':True,'writable_callback_pair_fully_represented_secondary_congruence_exclusion_found':True,'writable_callback_pair_fully_represented_two_gpr_frontier_empty':False,'writable_callback_pair_single_top_frontier_empty':False,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['12 of 27 sites are excluded; the remaining 15 remain compatible with at least one callback target.','This does not resolve the 1,095 missing-secondary sites or the broader single-TOP/TOP frontier.','Runtime mutation, stack/heap aliases and generated code remain open.'],'next_step':'Trace provenance for the 15 target-compatible folded-secondary sites; independently add bounded secondary-value provenance for the 1,095 missing-secondary sites.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
