#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94WriterSingletonDirectPropagation/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94RuntimeWriterSingletonProvenance/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ',',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],text=True,capture_output=True,check=True);out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM or not up['adjudication'].get('p13a_fun005ffc50_writable_callback_pair_d94_runtime_writer_singleton_provenance_subset_complete'):raise AssertionError('upstream incomplete')
 rows=dis(exe)
 if len(rows)!=2847850:raise AssertionError(('instruction count drift',len(rows)))
 refs=[r for r in rows if '0xbc185c' in r[2]]
 loads=[]
 for i,(a,m,o) in enumerate(rows):
  if '0xbc185c' not in o:continue
  x=re.match(r'(eax|ebx|ecx|edx|esi|edi|ebp),',o)
  if x:loads.append((i,a,x.group(1)))
 stack=[];nonstack=[];receivers=[];edx_calls=[]
 for i,origin,r in loads:
  aliases={r}
  for a,m,o in rows[i+1:i+31]:
   if m=='push' and o in aliases:
    pass
   if m=='mov' and ',' in o:
    dst,src=[x.strip() for x in o.split(',',1)]
    if src in aliases and '[' in dst:
     rec=(origin,a,o)
     (stack if re.search(r'\[(?:e|r)?(?:bp|sp)[+-]',dst) else nonstack).append(rec)
    if src in aliases and dst in REGS:aliases.add(dst)
    elif dst in aliases and dst in REGS:aliases.discard(dst)
   if m=='call':
    if 'ecx' in aliases:receivers.append((origin,a,o))
    if 'edx' in aliases:edx_calls.append((origin,a,o))
    break
   if m.startswith('j') or m.startswith('ret'):break
 if len(refs)!=115 or len(loads)!=113:raise AssertionError(('singleton ref/load drift',len(refs),len(loads)))
 if [a for _,a,_ in stack]!=[0x57b6e4,0xd77fad,0xd77fb0,0xd77fb3]:raise AssertionError(('stack store drift',[hex(a) for _,a,_ in stack]))
 if nonstack:raise AssertionError(('unexpected non-stack direct store',[(hex(o),hex(a),x) for o,a,x in nonstack]))
 if len(receivers)!=30 or len(edx_calls)!=2:raise AssertionError(('direct call propagation drift',len(receivers),len(edx_calls)))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'source':'DAT_00bc185c','method':'exact register copies within the straight-line block from each direct singleton load up to the first call/jump/return'},'proof':{'decoded_instruction_count':len(rows),'singleton_direct_reference_count':len(refs),'singleton_direct_load_count':len(loads),'same_block_stack_store_count':len(stack),'same_block_stack_store_sites':[f'0x{a:08x}' for _,a,_ in stack],'same_block_nonstack_store_count':len(nonstack),'same_block_ecx_receiver_call_count':len(receivers),'same_block_edx_argument_call_count':len(edx_calls)},'adjudication':{'p13a_fun005ffc50_writable_callback_pair_d94_writer_singleton_direct_propagation_subset_complete':True,'writable_callback_pair_d94_writer_singleton_same_block_nonstack_store_found':False,'writable_callback_pair_d94_writer_singleton_direct_store_into_loop_source_record_found':False,'writable_callback_pair_d94_writer_consumer_receiver_identity_proven':False,'writable_callback_pair_d94_runtime_writer_relevant_to_loop_bound_proven':False,'writable_callback_pair_d94_value_range_proven':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'writable_callback_pair_target_compatible_frontier_empty':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['The scan stops at the first control transfer and therefore does not claim interprocedural or multi-block alias closure.','Four same-block memory stores are stack locals only; zero same-block non-stack stores are observed.','Calls receiving the singleton can return or create aliases and remain open.'],'next_step':'Classify the 30 ECX-receiver and 2 EDX-argument call frontiers, and classify source_record+0 key semantics/producers independently before deciding writer relevance.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('exe',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('-o','--output',type=Path);a=ap.parse_args();r=analyze(a.exe,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
