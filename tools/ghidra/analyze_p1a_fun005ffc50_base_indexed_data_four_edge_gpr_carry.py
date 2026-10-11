#!/usr/bin/env python3
"""Bound base/index-derived GPR taint through up to four direct CFG edges."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, re
from collections import Counter, deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataFourEdgeGprCarry/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataImplicitPushPop/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
MAX_EDGES=4
MAX_STEPS=16

def helper():
 p=Path(__file__).with_name('analyze_p1a_fun005ffc50_base_indexed_data_implicit_push_pop.py')
 s=importlib.util.spec_from_file_location('p1a_baseidx_pushpop_helper',p)
 if not s or not s.loader:raise RuntimeError(p)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def direct_target(ops):
 q=re.match(r'^(?:0x)?([0-9a-fA-F]+)(?:\s|$)',ops)
 return int(q.group(1),16) if q else None

def transfer_gprs(h,mn,ops,regs):
 p=ops.split(',') if ops else [];regs=dict(regs);handled=False
 if mn=='mov' and len(p)==2 and p[0] in h.REGS and p[1] in h.REGS:
  handled=True;d,s=p
  if s in regs:regs[d]=regs[s]
  else:regs.pop(d,None)
 elif mn=='xchg' and len(p)==2 and p[0] in h.REGS and p[1] in h.REGS:
  handled=True;d,s=p;dv=regs.pop(d,None);sv=regs.pop(s,None)
  if dv is not None:regs[s]=dv
  if sv is not None:regs[d]=sv
 elif mn in h.DEST_DEP and p and p[0] in h.REGS:
  handled=True;d=p[0]
  if d in regs:
   erase=(len(p)>=2 and p[1]==d and mn in {'xor','sub'}) or (len(p)>=2 and p[1] in {'0','0x0'} and mn=='and')
   if erase:regs.pop(d,None)
   else:regs[d]=True
  elif h.writes_reg(mn,ops,d):regs.pop(d,None)
 elif mn=='imul' and len(p)>=2 and p[0] in h.REGS:
  handled=True;d,s=p[0],p[1]
  if s in regs:regs[d]=True
  else:regs.pop(d,None)
 elif mn=='lea' and len(p)==2 and p[0] in h.REGS:
  handled=True;d,s=p;src=[r for r in h.REGS if re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',s) and r in regs]
  if src:regs[d]=True
  else:regs.pop(d,None)
 if not handled:
  for r in list(regs):
   if h.writes_reg(mn,ops,r):regs.pop(r,None)
 return regs

def scan_cfg(rows,h=None):
 h=h or helper();rows=list(rows);by_addr={a:i for i,(a,_,_) in enumerate(rows)};addr_state={};seeds=[]
 for i,(a,mn,ops) in enumerate(rows):
  q=h.parse_load(mn,ops,h.state_values(addr_state))
  if q:seeds.append((i,a,*q))
  addr_state=h.update_state(mn,ops,addr_state)
 hits=[];edge_cross=Counter();terms=Counter();paths=0;branch_sites=set();max_edge=0
 for si,sa,reg,ea,src in seeds:
  q=deque([(si+1,{reg:False},0,0)])
  seen=set()
  while q:
   i,regs,steps,edges=q.popleft();paths+=1;max_edge=max(max_edge,edges)
   if i<0 or i>=len(rows):terms['out_of_range']+=1;continue
   key=(i,steps,edges,tuple(sorted(regs.items())))
   if key in seen:continue
   seen.add(key)
   if steps>=MAX_STEPS:terms['window_exhausted']+=1;continue
   a,mn,ops=rows[i];steps2=steps+1
   if mn=='call':
    if ops in regs:hits.append({'load_site':f'0x{sa:08x}','effective_address':f'0x{ea:08x}','transfer_site':f'0x{a:08x}','kind':'call','transfer_register':ops,'edge_depth':edges,'distance':steps2,'transformed':regs[ops]})
    terms['call_stop']+=1;continue
   if mn=='jmp':
    if ops in regs:
     hits.append({'load_site':f'0x{sa:08x}','effective_address':f'0x{ea:08x}','transfer_site':f'0x{a:08x}','kind':'jmp','transfer_register':ops,'edge_depth':edges,'distance':steps2,'transformed':regs[ops]});terms['indirect_jmp']+=1;continue
    t=direct_target(ops)
    if t is not None and t in by_addr and edges<MAX_EDGES:
     branch_sites.add(a);edge_cross[edges+1]+=1;q.append((by_addr[t],regs,steps2,edges+1));continue
    terms['jmp_stop']+=1;continue
   if mn.startswith('j') or mn.startswith('loop'):
    t=direct_target(ops)
    if t is not None and t in by_addr and edges<MAX_EDGES:
     branch_sites.add(a);edge_cross[edges+1]+=2;q.append((by_addr[t],dict(regs),steps2,edges+1))
     if i+1<len(rows):q.append((i+1,dict(regs),steps2,edges+1))
    else:terms['branch_stop']+=1
    continue
   if mn in h.CONTROL_STOPS or mn in {'ret','retn'}:terms['return_or_trap']+=1;continue
   regs2=transfer_gprs(h,mn,ops,regs)
   if not regs2:terms['all_taint_dead']+=1;continue
   q.append((i+1,regs2,steps2,edges))
 return {'decoded_instruction_count':len(rows),'base_indexed_data_load_count':len(seeds),'unique_effective_address_count':len({x[3] for x in seeds}),'explored_state_count':paths,'unique_direct_branch_site_count':len(branch_sites),'direct_edge_traversal_count_by_depth':{str(k):v for k,v in sorted(edge_cross.items())},'maximum_direct_edge_depth_reached':max_edge,'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,'termination_reason_counts':dict(sorted(terms.items()))}

def analyze(exe,upstream):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up['adjudication'].get('p13a_fun005ffc50_base_indexed_data_implicit_push_pop_subset_complete'):raise AssertionError('upstream incomplete')
 h=helper();r=scan_cfg(h.dis(exe),h)
 if (r['decoded_instruction_count'],r['base_indexed_data_load_count'],r['unique_effective_address_count'])!=(2847850,63,51):raise AssertionError(('inventory drift',r))
 if (r['explored_state_count'],r['unique_direct_branch_site_count'],r['maximum_direct_edge_depth_reached'])!=(1107,186,4):raise AssertionError(('cfg inventory drift',r))
 if r['direct_edge_traversal_count_by_depth']!={'1':88,'2':130,'3':107,'4':67}:raise AssertionError(('edge depth drift',r))
 if r['tainted_register_indirect_transfer_count']!=0:raise AssertionError(('unexpected transfer',r))
 if r['termination_reason_counts']!={'all_taint_dead':118,'branch_stop':15,'call_stop':67,'jmp_stop':8,'return_or_trap':8,'window_exhausted':19}:raise AssertionError(('termination drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'seed_model':'63 exact upstream base/index-addressed writable .data loads','maximum_direct_cfg_edges':MAX_EDGES,'maximum_decoded_instructions_after_load':MAX_STEPS,'path_model':'taken and fallthrough states remain separate; no predecessor merge/fixed point','carried_state':'GPR provenance with bounded copy/transform semantics; stack carriers remain covered only by separate upstream same-block contracts','call_policy':'calls stop the carried state','indirect_successor_policy':'never guessed'},'inventory':r,'adjudication':{'p13a_fun005ffc50_base_indexed_data_up_to_four_direct_cfg_edge_gpr_carry_subset_complete':True,'base_indexed_data_cfg_carried_register_indirect_transfer_found':False,'base_indexed_inter_block_carry_ruled_out':False,'base_indexed_writable_sources_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes only GPR provenance through at most four direct CFG edges and at most 16 decoded instructions after each of the 63 upstream base/index loads.','Fifth-plus edges, paths beyond 16 instructions, phi/fixed-point merging, stack state carried across edges, calls/returns, aliases and runtime/heap values remain open.','Retail reaches the four-edge cap and has 15 branch-stop plus 19 window-exhausted path states, so the aggregate inter-block gate remains fail-closed.'],'next_step':'Extend the remaining fifth-plus-edge/window-exhausted paths or classify them structurally; then address phi/fixed-point and runtime alias provenance.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
