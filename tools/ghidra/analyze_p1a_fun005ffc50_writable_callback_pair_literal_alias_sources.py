#!/usr/bin/env python3
"""Classify every exact address literal for writable callback slots 0x00b87b7c/0x00b87b80."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from collections import Counter
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairExactLiteralAliasSources/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairStaticProvenance/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TEXT_VA,TEXT_RAW,RDATA_RAW=0x00401000,0x00000400,0x006a4a00
SLOTS=(0x00b87b80,0x00b87b7c)
SNAPSHOTS={0x00b87b80:0x00a7fa5c,0x00b87b7c:0x00a7fa67}
EXPECTED={0x00b87b80:{'transfer':26,'write':2,'snapshot_load':1},0x00b87b7c:{'transfer':51,'write':2,'snapshot_load':1}}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True);out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def raw_occurrences(blob,value):
 q=struct.pack('<I',value);out=[];i=0
 while True:
  i=blob.find(q,i)
  if i<0:return out
  out.append(i);i+=1
def classify(mn,ops,slot,addr):
 exact=f'0x{slot:x}'
 if exact not in ops:return None
 if mn in {'call','jmp'} and ops==f'DWORD PTR ds:{exact}':return 'transfer'
 if mn=='mov' and ops.startswith(f'ds:{exact},'):return 'write'
 if mn=='mov' and ops.endswith(f'ds:{exact}') and addr==SNAPSHOTS[slot]:return 'snapshot_load'
 return 'other'
def analyze(exe:Path,upstream:Path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM or not up.get('adjudication',{}).get('p13a_fun005ffc50_writable_callback_pair_direct_static_provenance_subset_complete'):raise AssertionError('upstream incomplete')
 rows=dis(exe);results={}
 for slot in SLOTS:
  raw=raw_occurrences(blob,slot);hits=[];mapped=[]
  for idx,(a,mn,ops) in enumerate(rows):
   kind=classify(mn,ops,slot,a)
   if kind is None:continue
   if idx+1>=len(rows):raise AssertionError('terminal instruction')
   nxt=rows[idx+1][0];lo=TEXT_RAW+(a-TEXT_VA);hi=TEXT_RAW+(nxt-TEXT_VA);q=struct.pack('<I',slot)
   local=[];p=blob.find(q,lo,hi)
   while p>=0:
    local.append(p);p=blob.find(q,p+1,hi)
   if len(local)!=1:raise AssertionError(('literal mapping drift',hex(a),local))
   mapped.extend(local);hits.append({'site':f'0x{a:08x}','mnemonic':mn,'operands':ops,'classification':kind,'raw_offset':f'0x{local[0]:08x}'})
  counts=dict(sorted(Counter(x['classification'] for x in hits).items()))
  if counts!=EXPECTED[slot]:raise AssertionError(('classification drift',hex(slot),counts))
  if sorted(mapped)!=raw:raise AssertionError(('unclassified raw literal',hex(slot),raw,mapped))
  if any(x>=RDATA_RAW or x<TEXT_RAW for x in raw):raise AssertionError(('non-text exact literal',hex(slot),raw))
  results[f'0x{slot:08x}']={'raw_exact_va_literal_count':len(raw),'decoded_operand_literal_count':len(hits),'classification_counts':counts,'unclassified_exact_literal_count':0,'occurrences':hits}
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'slots':[f'0x{x:08x}' for x in SLOTS],'literal_shape':'exact little-endian 32-bit slot virtual address anywhere in retail image','proof':'every raw exact literal maps one-to-one into a decoded direct absolute memory operand; no exact slot VA literal remains elsewhere in the image'},'inventory':results,'adjudication':{'p13a_fun005ffc50_writable_callback_pair_exact_literal_alias_source_subset_complete':True,'writable_callback_pair_exact_slot_address_literals_fully_classified':True,'writable_callback_pair_exact_slot_address_literal_alias_source_found':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'encoded_or_reconstructed_callback_entry_ruled_out':False,'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This rules out only aliases whose source is an exact embedded 32-bit literal equal to either callback-slot VA.','Computed addresses (base+offset/index), copied runtime pointers, external mutation and reconstructed setter/config entry remain open.','No global alias, writable-memory, callback, slot0/slot1 or aggregate P1.3 gate is promoted.'],'next_step':'Trace computed base/index address formation that could resolve to 0x00b87b7c/0x00b87b80, then runtime/external mutation.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
