#!/usr/bin/env python3
"""Prove local induction bounds for four modulo-4 callback-alias frontier sites."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairMod4LocalInductionBounds/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairMod1LocalInductionBounds/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGETS=(0x00b87b7c,0x00b87b80); BASE=0x00aa9b60
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout;out=[]
 for line in p.stdout:
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 err=p.stderr.read() if p.stderr else ''
 if p.wait():raise RuntimeError(err)
 return out
def req(by,a,mn,ops):
 if by.get(a)!=(mn,ops):raise AssertionError((hex(a),by.get(a),(mn,ops)))
def prove(rows):
 by={a:(m,o) for a,m,o in rows}
 specs=[(0x00572951,'ecx',0x100,0x0057294b,0x0057296c,0x0057296f,0x00572974),(0x00878f82,'edx',0x400,0x00878f7c,0x00878f9d,0x00878fa0,0x00878fa5),(0x00a64930,'ecx',0x400,0x00a64927,0x00a6494b,0x00a6494e,0x00a64953),(0x00a64e40,'ecx',0x400,0x00a64e36,0x00a64e5b,0x00a64e5e,0x00a64e63)]
 out=[]
 for site,sec,limit,zero,add,cmpa,back in specs:
  req(by,zero,'xor','eax,eax'); req(by,site,'cmp',f'BYTE PTR [eax+{sec}*1],0x0'); req(by,add,'add','eax,0x4'); req(by,cmpa,'cmp',f'eax,0x{limit:x}'); req(by,back,'jb',f'0x{site:x}')
  hi=limit-4; lo=0; amin=BASE; amax=BASE+hi
  out.append({'site':f'0x{site:08x}','expression':f'eax+{sec}*1','primary_register':'eax','primary_min':lo,'primary_max':hi,'primary_stride':4,'secondary_singleton':f'0x{BASE:08x}','effective_address_min':f'0x{amin:08x}','effective_address_max':f'0x{amax:08x}','callback_target_possible':any(amin<=t<=amax for t in TARGETS)})
 return out
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_mod1_local_induction_bound_subset_complete'):raise AssertionError('upstream incomplete')
 rows=dis(exe);sites=prove(rows)
 if len(rows)!=2847850 or any(x['callback_target_possible'] for x in sites):raise AssertionError('retail proof drift')
 remaining=['0x00503328','0x0050334b','0x005d5621','0x007a6e9e','0x007a6ea5','0x007f25a0','0x0080b696']
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'method':'exact local four-byte string-scan induction bounds','secondary_singleton':f'0x{BASE:08x}','targets':[f'0x{x:08x}' for x in TARGETS]},'inventory':{'decoded_instruction_count':len(rows),'locally_bounded_site_count':4,'locally_bounded_sites':sites,'remaining_target_compatible_site_count':len(remaining),'remaining_target_compatible_sites':remaining},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_mod4_local_induction_bound_subset_complete':True,'writable_callback_pair_mod4_local_induction_exclusion_found':True,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_callback_pair_fully_represented_two_gpr_frontier_empty':False,'writable_callback_pair_single_top_frontier_empty':False,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['Four string-scan sites are excluded by exact local counter bounds.','Seven target-compatible sites remain after composing the mod1 and mod4 local exclusions.','Missing-secondary/runtime alias/global callback gates remain open.'],'next_step':'Trace the seven remaining target-compatible sites, prioritizing ESI producer provenance at 0x00503328/34b and 0x005d5621.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
