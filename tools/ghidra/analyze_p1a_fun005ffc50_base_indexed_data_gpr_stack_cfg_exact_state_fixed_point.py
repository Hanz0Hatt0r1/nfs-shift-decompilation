#!/usr/bin/env python3
"""Exhaust exact GPR+stack CFG states from base/index writable .data loads."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from collections import Counter, deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataGprStackCfgExactStateFixedPoint/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataGprCfgExactStateFixedPoint/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
def loadmod(name):
 p=Path(__file__).with_name(name);s=importlib.util.spec_from_file_location(name,p)
 if not s or not s.loader:raise RuntimeError(p)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def mods():
 fp=loadmod('analyze_p1a_fun005ffc50_base_indexed_data_gpr_cfg_exact_state_fixed_point.py');h=fp.helper();base=h.helper();stack=loadmod('analyze_p1a_fun005ffc50_base_indexed_data_stack_spill_reload.py');return h,base,stack
def transfer(h,base,stack,mn,ops,regs,mem,istack):
 p=ops.split(',') if ops else [];regs=dict(regs);mem=dict(mem);istack=list(istack);events=[]
 if mn=='push':
  flag=regs.get(ops);istack.append(flag);mem={k:v for k,v in mem.items() if k[0]!='esp'}
  if flag is not None:events.append(('push',flag,ops))
  return regs,mem,tuple(istack),events
 if mn=='pop':
  flag=istack.pop() if istack else None;mem={k:v for k,v in mem.items() if k[0]!='esp'}
  if ops in base.REGS:
   if flag is None:regs.pop(ops,None)
   else:regs[ops]=flag;events.append(('pop',flag,ops))
  return regs,mem,tuple(istack),events
 if mn in base.PUSH_UNKNOWN:
  istack.append(None);mem={k:v for k,v in mem.items() if k[0]!='esp'};return regs,mem,tuple(istack),events
 if mn in base.POP_UNKNOWN:
  if istack:istack.pop()
  mem={k:v for k,v in mem.items() if k[0]!='esp'};return regs,mem,tuple(istack),events
 handled=False
 if mn=='mov' and len(p)==2:
  d,s=p;ds=stack.stack_slot(d);ss=stack.stack_slot(s)
  if ds and s in base.REGS:
   handled=True
   if s in regs:mem[ds]=regs[s];events.append(('spill',regs[s],ds))
   else:mem.pop(ds,None)
  elif d in base.REGS and ss:
   handled=True
   if ss in mem:regs[d]=mem[ss];events.append(('reload',mem[ss],d))
   else:regs.pop(d,None)
 if not handled:regs=h.transfer_gprs(base,mn,ops,regs)
 if stack.invalidates_stack_base(mn,ops,'ebp'):mem={k:v for k,v in mem.items() if k[0]!='ebp'}
 if stack.invalidates_stack_base(mn,ops,'esp'):
  mem={k:v for k,v in mem.items() if k[0]!='esp'};istack=[]
 return regs,mem,tuple(istack),events
def scan(rows,h=None,base=None,stack=None):
 if not h or not base or not stack:h,base,stack=mods()
 rows=list(rows);by_addr={a:i for i,(a,_,_) in enumerate(rows)};addr_state={};seeds=[]
 for i,(a,mn,ops) in enumerate(rows):
  q=base.parse_load(mn,ops,base.state_values(addr_state))
  if q:seeds.append((i,a,*q))
  addr_state=base.update_state(mn,ops,addr_state)
 hits=[];terms=Counter();states=dups=0;branches=set();per=[];events=set();stack_edges=set();max_cells=0
 for si,sa,reg,ea,src in seeds:
  q=deque([(si+1,{reg:False},{},tuple())]);seen=set();seed_states=0
  while q:
   i,regs,mem,ist=q.popleft();key=(i,tuple(sorted(regs.items())),tuple(sorted((k[0],k[1],v) for k,v in mem.items())),ist)
   if key in seen:dups+=1;continue
   seen.add(key);states+=1;seed_states+=1;max_cells=max(max_cells,len(mem)+len(ist))
   if i<0 or i>=len(rows):terms['out_of_range']+=1;continue
   a,mn,ops=rows[i]
   if mn=='call':
    if ops in regs:hits.append((sa,a,'call',ops,regs[ops]))
    terms['call_stop']+=1;continue
   if mn=='jmp':
    if ops in regs:hits.append((sa,a,'jmp',ops,regs[ops]));terms['indirect_jmp']+=1;continue
    t=h.direct_target(ops)
    if t is not None and t in by_addr:
     branches.add(a)
     if mem or any(x is not None for x in ist):stack_edges.add((sa,a,t))
     q.append((by_addr[t],dict(regs),dict(mem),tuple(ist)))
    else:terms['unresolved_direct_or_indirect_jmp_stop']+=1
    continue
   if mn.startswith('j') or mn.startswith('loop'):
    t=h.direct_target(ops)
    if t is not None and t in by_addr:
     branches.add(a)
     if mem or any(x is not None for x in ist):
      stack_edges.add((sa,a,t));stack_edges.add((sa,a,rows[i+1][0] if i+1<len(rows) else -1))
     q.append((by_addr[t],dict(regs),dict(mem),tuple(ist)))
     if i+1<len(rows):q.append((i+1,dict(regs),dict(mem),tuple(ist)))
    else:terms['unresolved_branch_stop']+=1
    continue
   if mn in base.CONTROL_STOPS or mn in {'ret','retn'}:terms['return_or_trap']+=1;continue
   r2,m2,s2,ev=transfer(h,base,stack,mn,ops,regs,mem,ist)
   for e in ev:events.add((sa,a,e))
   if not r2 and not m2 and not any(x is not None for x in s2):terms['all_taint_dead']+=1;continue
   q.append((i+1,r2,m2,s2))
  per.append(seed_states)
 kinds=Counter(e[2][0] for e in events)
 return {'decoded_instruction_count':len(rows),'base_indexed_data_load_count':len(seeds),'unique_effective_address_count':len({x[3] for x in seeds}),'exact_gpr_stack_state_count':states,'duplicate_state_prune_count':dups,'unique_direct_branch_site_count':len(branches),'maximum_states_for_single_seed':max(per) if per else 0,'unique_stack_carry_branch_successor_count':len(stack_edges),'maximum_tracked_stack_cells':max_cells,'unique_stack_spill_event_count':kinds['spill'],'unique_stack_reload_event_count':kinds['reload'],'unique_tainted_push_event_count':kinds['push'],'unique_tainted_pop_reload_event_count':kinds['pop'],'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,'termination_reason_counts':dict(sorted(terms.items()))}
def analyze(exe,upstream):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_base_indexed_data_gpr_cfg_exact_state_fixed_point_subset_complete'):raise AssertionError('upstream incomplete')
 h,base,stack=mods();r=scan(base.dis(exe),h,base,stack)
 got=(r['decoded_instruction_count'],r['base_indexed_data_load_count'],r['unique_effective_address_count'],r['exact_gpr_stack_state_count'],r['duplicate_state_prune_count'],r['unique_direct_branch_site_count'],r['maximum_states_for_single_seed'],r['unique_stack_carry_branch_successor_count'],r['maximum_tracked_stack_cells'])
 if got!=(2847850,63,51,1106,80,201,83,8,3):raise AssertionError(('fixed-point drift',got,r))
 if (r['unique_stack_spill_event_count'],r['unique_stack_reload_event_count'],r['unique_tainted_push_event_count'],r['unique_tainted_pop_reload_event_count'])!=(2,1,35,0):raise AssertionError(('stack event drift',r))
 if r['tainted_register_indirect_transfer_count'] or r['termination_reason_counts']!={'all_taint_dead':104,'call_stop':70,'return_or_trap':7}:raise AssertionError(('transfer/termination drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'seed_model':'63 exact upstream base/index writable .data loads','state_key':'instruction index + exact GPR taint/transformed mapping + exact EBP/ESP mov stack cells + implicit push/pop taint stack','successor_model':'all resolved direct jump/conditional taken and fallthrough successors; indirect successors never guessed','call_policy':'calls terminate carried state after transfer check'},'inventory':r,'adjudication':{'p13a_fun005ffc50_base_indexed_data_gpr_stack_cfg_exact_state_fixed_point_subset_complete':True,'base_indexed_data_gpr_stack_cfg_exact_state_indirect_transfer_found':False,'base_indexed_stack_state_across_cfg_edges_ruled_out':True,'base_indexed_inter_block_carry_ruled_out':True,'base_indexed_writable_sources_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['Exact resolved-direct-CFG GPR+stack reachability only; calls stop and indirect successors are not guessed.','Arbitrary predecessor union/semantic phi reconstruction, writable aliases and runtime/heap mutation remain open.'],'next_step':'Classify writable-memory aliases and runtime mutation now that exact base/index GPR+stack inter-block carry is closed.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
