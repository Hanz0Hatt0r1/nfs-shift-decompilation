#!/usr/bin/env python3
"""Exhaust finite exact GPR-taint CFG states from base/index-addressed writable .data loads."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from collections import Counter, deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataGprCfgExactStateFixedPoint/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataFourEdgeGprCarry/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'

def helper():
 p=Path(__file__).with_name('analyze_p1a_fun005ffc50_base_indexed_data_four_edge_gpr_carry.py')
 s=importlib.util.spec_from_file_location('p1a_baseidx_cfg4_helper',p)
 if not s or not s.loader:raise RuntimeError(p)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def scan_fixed_point(rows,h=None):
 h=h or helper();base=h.helper();rows=list(rows);by_addr={a:i for i,(a,_,_) in enumerate(rows)};addr_state={};seeds=[]
 for i,(a,mn,ops) in enumerate(rows):
  q=base.parse_load(mn,ops,base.state_values(addr_state))
  if q:seeds.append((i,a,*q))
  addr_state=base.update_state(mn,ops,addr_state)
 hits=[];terms=Counter();branch_sites=set();states=0;cycle_prunes=0;per_seed=[]
 for si,sa,reg,ea,src in seeds:
  q=deque([(si+1,{reg:False})]);seen=set();seed_states=0
  while q:
   i,regs=q.popleft();key=(i,tuple(sorted(regs.items())))
   if key in seen:cycle_prunes+=1;continue
   seen.add(key);states+=1;seed_states+=1
   if i<0 or i>=len(rows):terms['out_of_range']+=1;continue
   a,mn,ops=rows[i]
   if mn=='call':
    if ops in regs:hits.append({'load_site':f'0x{sa:08x}','effective_address':f'0x{ea:08x}','transfer_site':f'0x{a:08x}','kind':'call','transfer_register':ops,'transformed':regs[ops]})
    terms['call_stop']+=1;continue
   if mn=='jmp':
    if ops in regs:
     hits.append({'load_site':f'0x{sa:08x}','effective_address':f'0x{ea:08x}','transfer_site':f'0x{a:08x}','kind':'jmp','transfer_register':ops,'transformed':regs[ops]});terms['indirect_jmp']+=1;continue
    t=h.direct_target(ops)
    if t is not None and t in by_addr:branch_sites.add(a);q.append((by_addr[t],dict(regs)))
    else:terms['unresolved_direct_or_indirect_jmp_stop']+=1
    continue
   if mn.startswith('j') or mn.startswith('loop'):
    t=h.direct_target(ops)
    if t is not None and t in by_addr:
     branch_sites.add(a);q.append((by_addr[t],dict(regs)))
     if i+1<len(rows):q.append((i+1,dict(regs)))
    else:terms['unresolved_branch_stop']+=1
    continue
   if mn in base.CONTROL_STOPS or mn in {'ret','retn'}:terms['return_or_trap']+=1;continue
   regs2=h.transfer_gprs(base,mn,ops,regs)
   if not regs2:terms['all_taint_dead']+=1;continue
   q.append((i+1,regs2))
  per_seed.append(seed_states)
 return {'decoded_instruction_count':len(rows),'base_indexed_data_load_count':len(seeds),'unique_effective_address_count':len({x[3] for x in seeds}),'exact_gpr_state_count':states,'cycle_or_join_duplicate_state_prune_count':cycle_prunes,'unique_direct_branch_site_count':len(branch_sites),'maximum_states_for_single_seed':max(per_seed) if per_seed else 0,'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,'termination_reason_counts':dict(sorted(terms.items()))}

def analyze(exe,upstream):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up['adjudication'].get('p13a_fun005ffc50_base_indexed_data_up_to_four_direct_cfg_edge_gpr_carry_subset_complete'):raise AssertionError('upstream incomplete')
 h=helper();base=h.helper();r=scan_fixed_point(base.dis(exe),h)
 if (r['decoded_instruction_count'],r['base_indexed_data_load_count'],r['unique_effective_address_count'])!=(2847850,63,51):raise AssertionError(('inventory drift',r))
 if (r['exact_gpr_state_count'],r['cycle_or_join_duplicate_state_prune_count'],r['unique_direct_branch_site_count'],r['maximum_states_for_single_seed'])!=(1063,78,199,83):raise AssertionError(('fixed point drift',r))
 if r['tainted_register_indirect_transfer_count']!=0:raise AssertionError(('unexpected transfer',r))
 if r['termination_reason_counts']!={'all_taint_dead':107,'call_stop':67,'return_or_trap':6}:raise AssertionError(('termination drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'seed_model':'63 exact upstream base/index-addressed writable .data loads','state_key':'instruction index plus exact GPR taint/transformed boolean mapping','successor_model':'all resolved direct jump/conditional taken and fallthrough successors; indirect successors never guessed','join_model':'no taint union or predecessor merge; identical exact states are deduplicated, yielding finite cycle-aware reachability','carried_state':'GPR provenance only using upstream bounded copy/transform transfer semantics','call_policy':'calls terminate carried state'},'inventory':r,'adjudication':{'p13a_fun005ffc50_base_indexed_data_gpr_cfg_exact_state_fixed_point_subset_complete':True,'base_indexed_data_gpr_cfg_exact_state_indirect_transfer_found':False,'base_indexed_gpr_inter_block_carry_ruled_out':True,'base_indexed_inter_block_carry_ruled_out':False,'base_indexed_stack_state_across_cfg_edges_ruled_out':False,'base_indexed_writable_sources_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This reaches a finite fixed point only for exact GPR taint states generated by the current transfer semantics and resolved direct CFG successors.','Stack/memory taint is not carried across CFG edges; aliases, call returns, unresolved indirect successors, richer value transforms and runtime/heap mutation remain open.','No predecessor union/phi abstraction is performed; equivalent exact states are deduplicated, so this does not prove arbitrary semantic phi reconstruction.'],'next_step':'Carry exact stack cells across CFG edges, then compose GPR+stack fixed-point reachability before addressing writable aliases and runtime mutation.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
