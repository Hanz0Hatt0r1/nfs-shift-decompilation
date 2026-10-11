#!/usr/bin/env python3
"""Bound absolute writable .data loads copied across GPRs before near indirect transfer."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun005ffc50AbsoluteDataCopyNearTransfer/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50AbsoluteDataLoadNearTransfer/1'
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
 if not (DATA_START<=addr<DATA_END):return None
 return d,addr,('modrm_absolute' if m.group(1) else 'moffs_absolute')

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
 active=[];copy_events=[];hits=[];terms=Counter();loads=0;slots=set();inst=0
 for a,mn,ops in rows:
  inst+=1;parts=ops.split(',') if ops else [];new=[]
  for st in active:
   st['age']+=1
   if mn in {'call','jmp'}:
    if ops in st['regs']:
     rec={'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'origin_register':st['origin'],
          'transfer_site':f'0x{a:08x}','kind':mn,'transfer_register':ops,'distance':st['age'],
          'copy_seen':st['copy_seen'],'transfer_uses_copied_register':ops!=st['origin']}
     hits.append(rec);terms['matched_transfer']+=1
    else:terms['other_control_transfer']+=1
    continue
   if mn.startswith('j') or mn.startswith('loop') or mn in CONTROL_STOPS or mn in {'ret','retn'}:
    terms['other_control_transfer']+=1;continue
   regs=set(st['regs'])
   if mn=='mov' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
    d,s=parts
    if s in regs:
     if d not in regs:
      regs.add(d);st['copy_seen']=True
      copy_events.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'origin_register':st['origin'],
                          'copy_site':f'0x{a:08x}','copy_kind':'mov','source_register':s,'destination_register':d,'distance':st['age']})
    else:regs.discard(d)
   elif mn=='xchg' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
    d,s=parts;dt=d in regs;ss=s in regs
    if dt!=ss:
     if dt:regs.remove(d);regs.add(s);src,dst=d,s
     else:regs.remove(s);regs.add(d);src,dst=s,d
     st['copy_seen']=True
     copy_events.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'origin_register':st['origin'],
                         'copy_site':f'0x{a:08x}','copy_kind':'xchg','source_register':src,'destination_register':dst,'distance':st['age']})
   else:
    for r in list(regs):
     if writes_reg(mn,ops,r):regs.discard(r)
   if not regs:terms['all_tainted_registers_clobbered']+=1;continue
   if st['age']>=WINDOW:terms['window_exhausted']+=1;continue
   st['regs']=regs;new.append(st)
  active=new
  q=parse_load(mn,ops)
  if q:
   reg,slot,_=q;loads+=1;slots.add(slot);active.append({'load':a,'slot':slot,'origin':reg,'regs':{reg},'age':0,'copy_seen':False})
 pair=Counter(f"{x['source_register']}->{x['destination_register']}" for x in copy_events)
 copied_loads={x['load_site'] for x in copy_events}
 copied_hits=[x for x in hits if x['copy_seen'] and x['transfer_uses_copied_register']]
 return {
  'decoded_instruction_count':inst,'absolute_data_load_count':loads,'unique_absolute_data_slot_count':len(slots),
  'copy_event_count':len(copy_events),'copied_load_count':len(copied_loads),'copy_count_by_pair':dict(sorted(pair.items())),
  'copy_events':copy_events,'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,
  'copied_register_indirect_transfer_count':len(copied_hits),'copied_register_indirect_transfers':copied_hits,
  'termination_reason_counts':dict(sorted(terms.items()))
 }

def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 ui=up['inventory'];ua=up['adjudication']
 if not ua.get('p13a_fun005ffc50_absolute_data_load_near_register_transfer_subset_complete'):raise AssertionError('upstream incomplete')
 if ui['absolute_data_load_count']!=1786 or ui['unique_absolute_data_slot_count']!=434:raise AssertionError('upstream load inventory drift')
 r=scan_rows(dis(exe))
 if r['decoded_instruction_count']!=2847850 or r['absolute_data_load_count']!=1786 or r['unique_absolute_data_slot_count']!=434:raise AssertionError(('retail inventory drift',r))
 if r['copy_event_count']!=10 or r['copied_load_count']!=10:raise AssertionError(('copy inventory drift',r['copy_event_count'],r['copied_load_count']))
 if r['copied_register_indirect_transfer_count'] or r['tainted_register_indirect_transfer_count']:raise AssertionError(('unexpected indirect transfer',r['tainted_register_indirect_transfers']))
 delta={
  'other_control_transfer':r['termination_reason_counts'].get('other_control_transfer',0)-ui['termination_reason_counts'].get('other_control_transfer',0),
  'register_clobber_to_all_tainted_clobbered':r['termination_reason_counts'].get('all_tainted_registers_clobbered',0)-ui['termination_reason_counts'].get('register_clobber',0),
  'window_exhausted':r['termination_reason_counts'].get('window_exhausted',0)-ui['termination_reason_counts'].get('window_exhausted',0),
 }
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},
  'scope':{'data_start':f'0x{DATA_START:08x}','data_end_exclusive':f'0x{DATA_END:08x}','forward_window_decoded_instructions':WINDOW,
           'provenance':'absolute .data dword load -> GPR, preserving identity through mov/xchg GPR copies only',
           'stops_on':['any call/jmp after transfer check','conditional branch/loop/ret/trap','clobber of every tainted GPR','16-instruction window']},
  'inventory':r,
  'upstream_termination_delta':delta,
  'adjudication':{
   'p13a_fun005ffc50_absolute_data_register_copy_near_transfer_subset_complete':True,
   'absolute_data_copied_register_indirect_transfer_found':False,
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
   'This closes only identity-preserving GPR copies (mov/xchg) of direct absolute .data loads within the same 16-decoded-instruction straight-line window.',
   'Pointer arithmetic/transforms, stack spill/reload, inter-block carry, base/indexed writable memory, aliases, heap/runtime values and wider points-to closure remain open.',
   'The 10 retail copy events produce zero indirect call/jmp through either the original or copied tainted register; two windows continue past the original-register clobber and terminate at unrelated control transfers.',
   'No global writable-memory, callback, reconstructed-entry, slot0, slot1, stored-alias or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Trace arithmetic/transformed or spill/reload writable-memory values, then base/indexed/alias sources; the direct absolute load plus same-block GPR-copy subset is now bounded.'
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
