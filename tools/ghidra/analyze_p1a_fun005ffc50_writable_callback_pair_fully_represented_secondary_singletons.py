#!/usr/bin/env python3
"""Classify the 27 single-TOP two-GPR sites whose secondary operand is always represented."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re
from collections import Counter,defaultdict,deque
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairFullyRepresentedSecondarySingletons/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairSingleTopSecondaryOperandInventory/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
EXPECTED_SITES=['0x004b9124','0x00503328','0x0050334b','0x00572951','0x00572957','0x0057295e','0x00572965','0x005d5621','0x006084d0','0x00608539','0x0060853f','0x007a6e9e','0x007a6ea5','0x007f25a0','0x0080b696','0x00878f82','0x00878f88','0x00878f8f','0x00878f96','0x00a64930','0x00a64936','0x00a6493d','0x00a64944','0x00a64e40','0x00a64e46','0x00a64e4d','0x00a64e54']
def load_model():
 p=Path(__file__).with_name('analyze_p1a_fun005ffc50_writable_callback_pair_may_state_widening_frontier.py');s=importlib.util.spec_from_file_location('p1a_cb_widen_model',p);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def expr_regs(expr,m):return set(re.findall(r'(?<![a-z0-9])('+'|'.join(sorted(m.REGS))+r')(?![a-z0-9])',expr))
def inspect_items(items,m):
 vals=[];tops=set();second=set();mn=set();expr=set()
 for x in items:
  mn.add(x['mnemonic']);expr.add(x['expr'])
  for r in expr_regs(x['expr'],m):
   v=x['state'].get(r)
   if v is m.TOP:tops.add(r)
   elif isinstance(v,frozenset):second.add(r);vals.append(v)
 return {'top_registers':tops,'secondary_registers':second,'secondary_values':vals,'mnemonics':mn,'expressions':expr}
def collect(rows,m):
 rows=list(rows);index={a:i for i,(a,_,__) in enumerate(rows)};seed={};c={}
 for i,(a,mn,ops) in enumerate(rows):
  before=dict(c)
  if mn=='jmp' or mn.startswith('j'):
   q=m.DIRECT.match(ops)
   if q and before:
    t=int(q.group(1),16);succ=[]
    if t in index:succ.append(index[t])
    if mn!='jmp' and i+1<len(rows):succ.append(i+1)
    for si in succ:seed[si]=m.merge_state(seed.get(si,{}),m.lift_exact(before))
  c=m.exact_update(mn,ops,c)
 state=dict(seed);q=deque(seed);obs=defaultdict(list)
 targets={int(x,16) for x in EXPECTED_SITES}
 while q:
  ii=q.popleft();c=dict(state[ii]);j=ii
  while j<len(rows):
   a,mn,ops=rows[j];before=dict(c)
   if a in targets:
    for mq in m.MEM.finditer(ops):
     ex=mq.group(1);rs=expr_regs(ex,m)
     if len(rs)==2 and sum(before.get(r) is m.TOP for r in rs)==1:obs[a].append({'mnemonic':mn,'expr':ex,'state':{r:before.get(r) for r in rs}})
   after=m.abs_update(mn,ops,c)
   if mn=='jmp' or mn.startswith('j'):
    dm=m.DIRECT.match(ops);succ=[]
    if dm and c:
     t=int(dm.group(1),16)
     if t in index:succ.append(index[t])
     if mn!='jmp' and j+1<len(rows):succ.append(j+1)
    for si in succ:
     old=state.get(si,{});merged=m.merge_state(old,c)
     if merged!=old:state[si]=merged;q.append(si)
    break
   if mn.startswith('loop') or mn in {'ret','retn'}|m.CONTROL:break
   c=after
   if not c:break
   j+=1
 mn=Counter();top=Counter();sec=Counter();pairs=Counter();sitevals=Counter();obsvals=Counter();samples=[];nobs=0;non_singleton=0
 for a in sorted(targets):
  it=obs[a];nobs+=len(it);z=inspect_items(it,m)
  for x in z['mnemonics']:mn[x]+=1
  for x in z['top_registers']:top[x]+=1
  for x in z['secondary_registers']:sec[x]+=1
  for x in z['top_registers']:
   for y in z['secondary_registers']:pairs[f'{x}->{y}']+=1
  union=set()
  for v in z['secondary_values']:
   if len(v)!=1:non_singleton+=1
   for x in v:obsvals[f'0x{x:08x}']+=1;union.add(x)
  for x in union:sitevals[f'0x{x:08x}']+=1
  samples.append({'site':f'0x{a:08x}','top_registers':sorted(z['top_registers']),'secondary_registers':sorted(z['secondary_registers']),'mnemonics':sorted(z['mnemonics']),'expressions':sorted(z['expressions']),'secondary_values':sorted(f'0x{x:08x}' for x in union)})
 return {'decoded_instruction_count':len(rows),'fully_represented_two_gpr_site_count':len(targets),'observation_count':nobs,'non_singleton_secondary_observation_count':non_singleton,'secondary_singleton_site_value_counts':dict(sorted(sitevals.items())),'secondary_singleton_observation_value_counts':dict(sorted(obsvals.items())),'mnemonic_site_counts':dict(sorted(mn.items())),'top_register_site_counts':dict(sorted(top.items())),'secondary_register_site_counts':dict(sorted(sec.items())),'top_to_secondary_pair_site_counts':dict(sorted(pairs.items())),'sites':samples}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest();
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_single_top_secondary_operand_inventory_subset_complete'):raise AssertionError('upstream incomplete')
 if up['inventory'].get('fully_represented_two_gpr_sites')!=EXPECTED_SITES:raise AssertionError('upstream site drift')
 m=load_model();r=collect(m.dis(exe),m)
 exp=(2847850,27,32,0,{'0x00000000':6,'0x00aa9b60':21},{'0x00000000':9,'0x00aa9b60':23},{'cmp':19,'lea':3,'mov':5})
 got=(r['decoded_instruction_count'],r['fully_represented_two_gpr_site_count'],r['observation_count'],r['non_singleton_secondary_observation_count'],r['secondary_singleton_site_value_counts'],r['secondary_singleton_observation_value_counts'],r['mnemonic_site_counts'])
 if got!=exp:raise AssertionError(('singleton secondary drift',got))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'frontier':'the 27 upstream two-GPR single-TOP sites whose secondary operand is represented in every original may-state observation','classification':'verify every represented secondary value is singleton and inventory the exact singleton constants','interpretation':'a singleton secondary may be folded into the affine memory expression; this contract does not classify the widened TOP primary operand'},'inventory':r,'adjudication':{'p13a_fun005ffc50_writable_callback_pair_fully_represented_secondary_singleton_subset_complete':True,'writable_callback_pair_fully_represented_secondary_values_all_singleton':True,'writable_callback_pair_fully_represented_two_gpr_frontier_empty':False,'writable_callback_pair_single_top_frontier_empty':False,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This proves only that the secondary operand at these 27 sites is an exact singleton in every observed may-state.','The widened primary operand still needs congruence/provenance classification after the singleton is folded into the affine expression.','The 1,095 missing-secondary sites and all broader alias/runtime frontiers remain open.'],'next_step':'Fold the singleton secondary into each of the 27 affine expressions and apply the congruence/provenance domain to the remaining primary operand.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
