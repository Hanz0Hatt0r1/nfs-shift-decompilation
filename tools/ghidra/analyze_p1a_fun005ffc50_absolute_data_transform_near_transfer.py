#!/usr/bin/env python3
"""Bound arithmetic/LEA transforms of absolute writable .data-loaded values before near indirect transfer."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun005ffc50AbsoluteDataTransformNearTransfer/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50AbsoluteDataCopyNearTransfer/1'
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
DEST_DEP={'add','sub','xor','or','and','adc','sbb','shl','sal','shr','sar','rol','ror','rcl','rcr','inc','dec','neg','not'}

def norm(s:str)->str:return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')

def dis(exe:Path):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace')
 assert p.stdout
 for line in p.stdout:
  m=I.match(line)
  if m:yield int(m.group(1),16),m.group(2).lower(),norm(m.group(3))
 err=p.stderr.read() if p.stderr else ''
 if p.wait():raise RuntimeError(err)

def parse_load(mn:str,ops:str):
 if mn!='mov' or ',' not in ops:return None
 d,s=ops.split(',',1)
 if d not in REGS:return None
 m=ABS_LOAD.fullmatch(s)
 if not m:return None
 addr=int(m.group(2),16)
 if DATA_START<=addr<DATA_END:return d,addr
 return None

def writes_reg(mn:str,ops:str,reg:str)->bool:
 parts=ops.split(',') if ops else []
 if mn=='xchg' and any(x==reg or SUB.get(x)==reg for x in parts):return True
 if parts and mn not in READ_ONLY_FIRST:
  d=parts[0]
  if d==reg or SUB.get(d)==reg:return True
 if reg in {'eax','edx'} and mn in {'mul','div','idiv','cdq','cwd','cwde'}:return True
 if reg in {'eax','edx'} and mn=='imul' and len(parts)==1:return True
 return False

def scan_rows(rows):
 active=[];events=[];hits=[];terms=Counter();loads=0;slots=set();inst=0
 for a,mn,ops in rows:
  inst+=1;parts=ops.split(',') if ops else [];new=[]
  for st in active:
   st['age']+=1
   if mn in {'call','jmp'}:
    if ops in st['regs']:
     hits.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'transfer_site':f'0x{a:08x}',
                  'kind':mn,'transfer_register':ops,'distance':st['age'],'transformed':st['regs'][ops]})
     terms['matched_transfer']+=1
    else:terms['other_control_transfer']+=1
    continue
   if mn.startswith('j') or mn.startswith('loop') or mn in CONTROL_STOPS or mn in {'ret','retn'}:
    terms['other_control_transfer']+=1;continue
   regs=dict(st['regs'])
   event=None
   if mn=='mov' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
    d,s=parts
    if s in regs:regs[d]=regs[s]
    else:regs.pop(d,None)
   elif mn=='xchg' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
    d,s=parts;dv=regs.pop(d,None);sv=regs.pop(s,None)
    if dv is not None:regs[s]=dv
    if sv is not None:regs[d]=sv
   elif mn in DEST_DEP and parts and parts[0] in REGS:
    d=parts[0]
    if d in regs:
     erase=(len(parts)>=2 and parts[1]==d and mn in {'xor','sub'}) or (len(parts)>=2 and parts[1] in {'0','0x0'} and mn=='and')
     if erase:regs.pop(d,None)
     else:regs[d]=True;event=(mn,d)
    elif writes_reg(mn,ops,d):regs.pop(d,None)
   elif mn=='imul' and len(parts)>=2 and parts[0] in REGS:
    d,s=parts[0],parts[1]
    if s in regs:regs[d]=True;event=(mn,d)
    else:regs.pop(d,None)
   elif mn=='lea' and len(parts)==2 and parts[0] in REGS:
    d,s=parts
    src=[r for r in REGS if re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',s) and r in regs]
    if src:regs[d]=True;event=(mn,d)
    else:regs.pop(d,None)
   else:
    for r in list(regs):
     if writes_reg(mn,ops,r):regs.pop(r,None)
   if event:
    events.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'transform_site':f'0x{a:08x}',
                   'mnemonic':mn,'instruction':f'{mn} {ops}'.rstrip(),'destination_register':event[1],'distance':st['age']})
   if not regs:terms['all_tainted_registers_clobbered']+=1;continue
   if st['age']>=WINDOW:terms['window_exhausted']+=1;continue
   st['regs']=regs;new.append(st)
  active=new
  q=parse_load(mn,ops)
  if q:
   reg,slot=q;loads+=1;slots.add(slot);active.append({'load':a,'slot':slot,'regs':{reg:False},'age':0})
 transformed_hits=[x for x in hits if x['transformed']]
 by=Counter(x['mnemonic'] for x in events)
 return {
  'decoded_instruction_count':inst,'absolute_data_load_count':loads,'unique_absolute_data_slot_count':len(slots),
  'transform_event_count':len(events),'transformed_load_count':len({x['load_site'] for x in events}),
  'unique_transform_site_count':len({x['transform_site'] for x in events}),'transform_count_by_mnemonic':dict(sorted(by.items())),
  'transform_event_samples':events[:12]+events[-4:] if len(events)>16 else events,
  'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,
  'transformed_register_indirect_transfer_count':len(transformed_hits),'transformed_register_indirect_transfers':transformed_hits,
  'termination_reason_counts':dict(sorted(terms.items()))
 }

def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up['adjudication'].get('p13a_fun005ffc50_absolute_data_register_copy_near_transfer_subset_complete'):raise AssertionError('upstream copy subset incomplete')
 if up['inventory']['absolute_data_load_count']!=1786 or up['inventory']['copy_event_count']!=10:raise AssertionError('upstream inventory drift')
 r=scan_rows(dis(exe))
 expected={'add':26,'and':9,'dec':4,'imul':1,'inc':4,'lea':45,'or':2,'shl':1,'sub':3,'xor':84}
 if r['decoded_instruction_count']!=2847850 or r['absolute_data_load_count']!=1786 or r['unique_absolute_data_slot_count']!=434:raise AssertionError(('retail inventory drift',r))
 if r['transform_event_count']!=179 or r['transformed_load_count']!=160 or r['unique_transform_site_count']!=164 or r['transform_count_by_mnemonic']!=expected:
  raise AssertionError(('transform inventory drift',r))
 if r['tainted_register_indirect_transfer_count'] or r['transformed_register_indirect_transfer_count']:raise AssertionError(('unexpected transfer',r['tainted_register_indirect_transfers']))
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},
  'scope':{'data_start':f'0x{DATA_START:08x}','data_end_exclusive':f'0x{DATA_END:08x}','forward_window_decoded_instructions':WINDOW,
           'identity_copy_ops':['mov GPR,GPR','xchg GPR,GPR'],
           'dependency_preserving_transform_ops':sorted(DEST_DEP|{'imul','lea'}),
           'dependency_erasing_special_cases':['xor reg,reg','sub reg,reg','and reg,0'],
           'stops_on':['any call/jmp after transfer check','conditional branch/loop/ret/trap','clobber of every tainted GPR','16-instruction window']},
  'inventory':r,
  'adjudication':{
   'p13a_fun005ffc50_absolute_data_transform_near_transfer_subset_complete':True,
   'absolute_data_transformed_register_indirect_transfer_found':False,
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
   'This is a dependency-taint subset, not exact pointer-value recovery: selected arithmetic/bitwise/shift/LEA transforms preserve whether a value depends on an absolute .data load.',
   'Stack spill/reload, memory-to-memory aliases, inter-block carry, base/indexed writable sources, heap/runtime values, return values, and unmodelled transforms remain open.',
   'Across 179 bounded transform events from 160 loads, no indirect call/jmp consumes a tainted or transformed register.',
   'No global writable-memory, callback, reconstructed-entry, slot0, slot1, stored-alias or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Trace stack spill/reload and inter-block writable-memory provenance, then base/indexed/alias sources; bounded same-block copy plus selected transform paths are now negative.'
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
