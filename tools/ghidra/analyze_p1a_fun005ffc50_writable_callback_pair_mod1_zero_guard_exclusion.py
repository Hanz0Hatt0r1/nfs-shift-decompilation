#!/usr/bin/env python3
"""Exclude one remaining modulus-1 callback-alias site via an exact retail zero guard."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairMod1ZeroGuardExclusion/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairMod4LocalInductionBounds/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGETS=(0x00b87b7c,0x00b87b80); BASE=0x00aa9b60; SITE=0x005d5621
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
H=re.compile(r'^\s*\d+\s+([^\s]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+2\*\*\d+')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe:Path):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout;out=[]
 for line in p.stdout:
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 err=p.stderr.read() if p.stderr else ''
 if p.wait():raise RuntimeError(err)
 return out
def section_map(exe:Path):
 p=subprocess.run(['objdump','-h',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=H.match(line)
  if m:out.append((m.group(1),int(m.group(2),16),int(m.group(3),16),int(m.group(5),16)))
 return out
def read_va(exe:Path,va:int,size:int=1):
 for name,sec_size,vma,file_off in section_map(exe):
  if vma<=va and va+size<=vma+sec_size:
   with exe.open('rb') as f:f.seek(file_off+(va-vma));data=f.read(size)
   if len(data)!=size:raise AssertionError('short read')
   return name,data
 raise AssertionError(('unmapped VA',hex(va)))
def require(by,a,mn,ops):
 got=by.get(a)
 if got!=(mn,ops):raise AssertionError((hex(a),got,(mn,ops)))
def prove(rows,exe:Path):
 by={a:(m,o) for a,m,o in rows}
 require(by,0x005d55de,'xor','esi,esi')
 require(by,0x005d5603,'mov','ebp,0xaa9b60')
 require(by,0x005d560c,'cmp','BYTE PTR [ebp+0x0],0x0')
 require(by,0x005d5614,'je','0x5d562b')
 require(by,SITE,'cmp','BYTE PTR [esi+ebp*1],0x0')
 sec,data=read_va(exe,BASE,1)
 if sec!='.rdata' or data!=b'\x00':raise AssertionError(('base byte drift',sec,data.hex()))
 return {'site':f'0x{SITE:08x}','expression':'esi+ebp*1','primary_register':'esi','secondary_register':'ebp','secondary_singleton':f'0x{BASE:08x}','base_section':sec,'base_first_byte':'0x00','guard_site':'0x005d560c','guard_taken_target':'0x005d562b','site_reachable_under_secondary_singleton':False,'callback_target_possible':False}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_mod4_local_induction_bound_subset_complete'):raise AssertionError('upstream incomplete')
 prior=up['inventory'].get('remaining_target_compatible_sites')
 expected=['0x00503328','0x0050334b','0x005d5621','0x007a6e9e','0x007a6ea5','0x007f25a0','0x0080b696']
 if prior!=expected:raise AssertionError(('frontier drift',prior))
 rows=dis(exe);site=prove(rows,exe)
 if len(rows)!=2847850:raise AssertionError(('instruction count drift',len(rows)))
 remaining=[x for x in prior if x!=site['site']]
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'method':'exact branch-feasibility proof using the upstream singleton secondary operand and the retail .rdata byte at that address','targets':[f'0x{x:08x}' for x in TARGETS]},'inventory':{'decoded_instruction_count':len(rows),'upstream_target_compatible_site_count':len(prior),'zero_guard_excluded_site_count':1,'zero_guard_excluded_sites':[site],'remaining_target_compatible_site_count':len(remaining),'remaining_target_compatible_sites':remaining},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_mod1_zero_guard_exclusion_subset_complete':True,'writable_callback_pair_mod1_zero_guard_exclusion_found':True,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_callback_pair_fully_represented_two_gpr_frontier_empty':False,'writable_callback_pair_single_top_frontier_empty':False,'writable_callback_pair_may_state_top_frontier_empty':False,'writable_callback_pair_multi_edge_computed_alias_sources_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This excludes only 0x005d5621 under the already-proven EBP=0x00aa9b60 singleton observation.','The two ESI+EBX*2 sites at 0x00503328/0x0050334b still depend on a runtime loop-count bound.','The four remaining modulo-4/8 sites, missing-secondary/runtime aliases and aggregate P1.3 gates remain open.'],'next_step':'Trace the runtime count provenance feeding ESI at 0x00503328/0x0050334b; then classify the four remaining modulo-4/8 target-compatible sites.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
