#!/usr/bin/env python3
"""Prove local induction bounds for four modulus-1 callback-alias frontier sites."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairMod1LocalInductionBounds/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairTargetCompatibleCongruenceFrontier/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGETS=(0x00b87b7c,0x00b87b80); BASE=0x00aa9b60
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s): return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe:Path):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace'); assert p.stdout
 out=[]
 for line in p.stdout:
  m=I.match(line)
  if m: out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 err=p.stderr.read() if p.stderr else ''
 if p.wait(): raise RuntimeError(err)
 return out
def require(by,a,mn,ops):
 got=by.get(a)
 if got!=(mn,ops): raise AssertionError((hex(a),got,(mn,ops)))
def prove(rows):
 by={a:(mn,ops) for a,mn,ops in rows}
 require(by,0x004b911a,'xor','eax,eax'); require(by,0x004b9124,'cmp','BYTE PTR [eax+ecx*1],0x0')
 require(by,0x004b912a,'add','eax,0x1'); require(by,0x004b912d,'cmp','eax,0x1'); require(by,0x004b9130,'jb','0x4b9124')
 require(by,0x006084ba,'xor','edi,edi'); require(by,0x006084c4,'cmp','edi,0xff'); require(by,0x006084ca,'jae','0x6084db')
 require(by,0x006084d0,'mov','al,BYTE PTR [edi+ebp*1+0x1]'); require(by,0x006084d4,'add','edi,0x1')
 require(by,0x00608539,'cmp','BYTE PTR [edi+ebp*1],0x3a'); require(by,0x0060853f,'lea','edi,[edi+ebp*1+0x1]')
 specs=[
  (0x004b9124,'eax+ecx*1','eax',0,0,0),
  (0x006084d0,'edi+ebp*1+0x1','edi',0,254,1),
  (0x00608539,'edi+ebp*1','edi',0,255,0),
  (0x0060853f,'edi+ebp*1+0x1','edi',0,255,1),
 ]
 sites=[]
 for a,expr,reg,lo,hi,disp in specs:
  amin=BASE+lo+disp; amax=BASE+hi+disp
  possible=any(amin<=t<=amax for t in TARGETS)
  sites.append({'site':f'0x{a:08x}','expression':expr,'primary_register':reg,'primary_min':lo,'primary_max':hi,'secondary_singleton':f'0x{BASE:08x}','effective_address_min':f'0x{amin:08x}','effective_address_max':f'0x{amax:08x}','callback_target_possible':possible})
 return sites
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA: raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_target_compatible_congruence_frontier_subset_complete'): raise AssertionError('upstream incomplete')
 mod1=[x['site'] for x in up['inventory']['sites'] if x['terminal_class']=='0 mod 1']
 if mod1!=['0x004b9124','0x00503328','0x0050334b','0x005d5621','0x006084d0','0x00608539','0x0060853f']: raise AssertionError(('mod1 drift',mod1))
 rows=dis(exe); sites=prove(rows)
 if len(rows)!=2847850 or any(x['callback_target_possible'] for x in sites): raise AssertionError('retail proof drift')
 resolved={x['site'] for x in sites}; remaining=[x for x in mod1 if x not in resolved]
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'frontier':'seven terminal 0 mod 1 target-compatible sites from the upstream congruence inventory','method':'exact local induction bounds from explicit zero initialization, immediate increment, compare and direct back-edge/exit guards','secondary_singleton':f'0x{BASE:08x}','targets':[f'0x{x:08x}' for x in TARGETS]},'inventory':{'decoded_instruction_count':len(rows),'upstream_mod1_site_count':7,'locally_bounded_site_count':4,'locally_bounded_sites':sites,'remaining_mod1_site_count':len(remaining),'remaining_mod1_sites':remaining},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_mod1_local_induction_bound_subset_complete':True,'writable_callback_pair_mod1_local_induction_exclusion_found':True,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_callback_pair_fully_represented_two_gpr_frontier_empty':False,'writable_callback_pair_single_top_frontier_empty':False,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This proves only four local induction-counter sites among the seven modulus-1 sites.','The three remaining modulus-1 sites at 0x00503328, 0x0050334b and 0x005d5621 require producer/join provenance.','The eight modulo-4/8 compatible sites and the separate 1,095 missing-secondary class remain open.'],'next_step':'Trace producer/join provenance for ESI at 0x00503328, 0x0050334b and 0x005d5621, then return to the eight modulo-4/8 compatible sites.'}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('executable',type=Path); ap.add_argument('--upstream',type=Path,required=True); ap.add_argument('--output',type=Path); a=ap.parse_args(); r=analyze(a.executable,a.upstream); s=json.dumps(r,indent=2,sort_keys=True)+'\n'; a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__': main()
