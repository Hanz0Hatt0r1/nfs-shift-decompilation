#!/usr/bin/env python3
"""Bound direct absolute .data load -> near call/jmp through the loaded GPR."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun005ffc50AbsoluteDataLoadNearTransfer/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50DirectAbsoluteWritableTransferComposition/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
DATA_START,DATA_END=0x00b81000,0x00bbc600
WINDOW=16
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
ABS_LOAD=re.compile(r'^(?:(DWORD PTR )?ds:)0x([0-9a-fA-F]+)$')
READ_ONLY_FIRST={
 'cmp','test','push','call','jmp','bt','btc','btr','bts','prefetchnta','prefetcht0','prefetcht1','prefetcht2',
 'je','jne','jz','jnz','ja','jae','jb','jbe','jg','jge','jl','jle','jo','jno','js','jns','jp','jnp','jcxz','jecxz',
 'loop','loope','loopne','ret','retn','iret','iretd','nop'
}
CONTROL_STOPS={'int','int3','ud2','iret','iretd'}

def norm(s:str)->str:return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')

def dis(exe:Path):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out

def parse_load(mn:str,ops:str):
 if mn!='mov' or ',' not in ops:return None
 d,s=ops.split(',',1)
 if d not in REGS:return None
 m=ABS_LOAD.fullmatch(s)
 if not m:return None
 addr=int(m.group(2),16)
 if not (DATA_START<=addr<DATA_END):return None
 form='modrm_absolute' if m.group(1) else 'moffs_absolute'
 return d,addr,form

def writes_reg(mn:str,ops:str,reg:str)->bool:
 parts=ops.split(',') if ops else []
 if mn=='xchg' and any(x==reg or SUB.get(x)==reg for x in parts):return True
 if parts and mn not in READ_ONLY_FIRST:
  d=parts[0]
  if d==reg or SUB.get(d)==reg:return True
 if reg in {'eax','edx'} and mn in {'mul','div','idiv'}:return True
 if reg in {'eax','edx'} and mn in {'cdq','cwd','cwde'}:return True
 if reg in {'eax','edx'} and mn=='imul' and len(parts)==1:return True
 return False

def scan_rows(rows):
 loads=[];hits=[];term=Counter();regc=Counter();formc=Counter()
 for i,(a,mn,ops) in enumerate(rows):
  q=parse_load(mn,ops)
  if not q:continue
  reg,slot,form=q;loads.append((i,a,reg,slot,form));regc[reg]+=1;formc[form]+=1
  stopped=False
  for distance,j in enumerate(range(i+1,min(i+WINDOW+1,len(rows))),start=1):
   aa,mm,oo=rows[j]
   if mm in {'call','jmp'}:
    if oo==reg:
     hits.append({'load_site':f'0x{a:08x}','slot':f'0x{slot:08x}','register':reg,'transfer_site':f'0x{aa:08x}','kind':mm,'distance':distance})
     term['matched_transfer']+=1
    else:term['other_control_transfer']+=1
    stopped=True;break
   if mm.startswith('j') or mm.startswith('loop') or mm.startswith('ret') or mm in CONTROL_STOPS:
    term['other_control_transfer']+=1;stopped=True;break
   if writes_reg(mm,oo,reg):
    term['register_clobber']+=1;stopped=True;break
  if not stopped:term['window_exhausted']+=1
 return {
  'absolute_data_load_count':len(loads),
  'unique_absolute_data_slot_count':len({x[3] for x in loads}),
  'load_count_by_register':dict(sorted(regc.items())),
  'load_count_by_encoding_form':dict(sorted(formc.items())),
  'near_loaded_register_indirect_transfer_count':len(hits),
  'near_loaded_register_indirect_transfers':hits,
  'termination_reason_counts':dict(sorted(term.items())),
 }

def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up.get('adjudication',{}).get('p13a_fun005ffc50_direct_absolute_writable_indirect_transfer_slot_inventory_complete'):
  raise AssertionError('upstream direct-absolute writable inventory incomplete')
 rows=dis(exe);r=scan_rows(rows)
 expected_regs={'eax':1125,'ebp':1,'ebx':25,'ecx':326,'edi':72,'edx':186,'esi':51}
 expected_forms={'modrm_absolute':661,'moffs_absolute':1125}
 expected_terms={'other_control_transfer':1355,'register_clobber':413,'window_exhausted':18}
 if len(rows)!=2847850 or r['absolute_data_load_count']!=1786 or r['unique_absolute_data_slot_count']!=434:
  raise AssertionError(('load inventory drift',len(rows),r))
 if r['load_count_by_register']!=expected_regs or r['load_count_by_encoding_form']!=expected_forms:
  raise AssertionError(('load shape drift',r))
 if r['termination_reason_counts']!=expected_terms:raise AssertionError(('termination drift',r['termination_reason_counts']))
 if r['near_loaded_register_indirect_transfer_count'] or r['near_loaded_register_indirect_transfers']:
  raise AssertionError(('near loaded-register transfer positive',r['near_loaded_register_indirect_transfers']))
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},
  'scope':{
   'target_context':'FUN_005ffc50 writable-memory incoming-entry frontier',
   'decoded_instruction_count':len(rows),
   'data_start':'0x00b81000','data_end_exclusive':'0x00bbc600',
   'load_shape':'mov 32-bit GPR, absolute ds:.data memory contents',
   'forward_window_decoded_instructions':WINDOW,
   'stop_conditions':['any call/jmp after same-register transfer check','conditional branch/loop/ret/trap','write/clobber of loaded GPR or subregister'],
  },
  'inventory':r,
  'adjudication':{
   'p13a_fun005ffc50_absolute_data_load_near_register_transfer_subset_complete':True,
   'absolute_data_load_near_register_indirect_transfer_found':False,
   'register_loaded_or_aliased_writable_slots_ruled_out':False,
   'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
   'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,
   'return_value_fun005ffc50_provenance_ruled_out':False,
   'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,
   'encoded_or_reconstructed_callback_entry_ruled_out':False,
   'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,
   'fun0067b660_callback_argument_provenance_complete':False,
   'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
   'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
   'This closes only a loaded-register near-use subset: an absolute .data dword is loaded directly into one GPR and that same GPR is checked for call/jmp use within 16 decoded instructions before control flow or clobber.',
   'Register copies, spill/reload, arithmetic transformations of the loaded pointer, base/index-addressed memory, inter-block carry, alias stores, and heap/runtime-generated pointers remain open.',
   'Immediate loads of a .data address are not memory-content loads and are intentionally excluded from the 1,786-load inventory.',
   'No global writable-memory, callback, reconstructed-entry, slot0, slot1, stored-alias or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Trace copied/transformed/inter-block writable-memory values, base/indexed slots, or alias writers; the direct absolute .data load -> same-register near transfer subset is now bounded.'
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
