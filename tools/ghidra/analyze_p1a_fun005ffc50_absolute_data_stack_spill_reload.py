#!/usr/bin/env python3
"""Bound exact EBP/ESP stack spill/reload provenance from absolute writable .data loads."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun005ffc50AbsoluteDataStackSpillReload/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50AbsoluteDataTransformNearTransfer/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
DATA_START,DATA_END=0x00b81000,0x00bbc600
WINDOW=16
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
ABS_LOAD=re.compile(r'^(?:(DWORD PTR )?ds:)0x([0-9a-fA-F]+)$')
STACK_SLOT=re.compile(r'^(?:DWORD PTR )?\[(ebp|esp)([+-]0x[0-9a-fA-F]+)?\]$')
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
 return (d,addr) if DATA_START<=addr<DATA_END else None

def stack_slot(op:str):
 m=STACK_SLOT.fullmatch(op)
 if not m:return None
 return m.group(1),m.group(2) or '+0x0'

def writes_reg(mn:str,ops:str,reg:str)->bool:
 parts=ops.split(',') if ops else []
 if mn=='xchg' and any(x==reg or SUB.get(x)==reg for x in parts):return True
 if parts and mn not in READ_ONLY_FIRST:
  d=parts[0]
  if d==reg or SUB.get(d)==reg:return True
 if reg in {'eax','edx'} and mn in {'mul','div','idiv','cdq','cwd','cwde'}:return True
 if reg in {'eax','edx'} and mn=='imul' and len(parts)==1:return True
 return False

def invalidates_stack_base(mn:str,ops:str,base:str)->bool:
 parts=ops.split(',') if ops else []
 if base=='esp' and mn in {'push','pop','pushf','popf','pusha','popa','enter','leave'}:return True
 aliases={'esp','sp'} if base=='esp' else {'ebp','bp'}
 return bool(parts and parts[0] in aliases and mn not in READ_ONLY_FIRST)

def scan_rows(rows):
 active=[];spills=[];reloads=[];hits=[];terms=Counter();loads=0;slots=set();inst=0
 for a,mn,ops in rows:
  inst+=1;parts=ops.split(',') if ops else [];new=[]
  for st in active:
   st['age']+=1
   if mn in {'call','jmp'}:
    if ops in st['regs']:
     hits.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'transfer_site':f'0x{a:08x}',
                  'kind':mn,'transfer_register':ops,'distance':st['age'],'transformed':st['regs'][ops],
                  'reload_seen':st['reload_seen']})
     terms['matched_transfer']+=1
    else:terms['other_control_transfer']+=1
    continue
   if mn.startswith('j') or mn.startswith('loop') or mn in CONTROL_STOPS or mn in {'ret','retn'}:
    terms['other_control_transfer']+=1;continue
   regs=dict(st['regs']);mem=dict(st['mem']);handled=False
   inv_ebp=invalidates_stack_base(mn,ops,'ebp');inv_esp=invalidates_stack_base(mn,ops,'esp')
   if mn=='mov' and len(parts)==2:
    d,s=parts;dst_slot=stack_slot(d);src_slot=stack_slot(s)
    if dst_slot and s in REGS:
     handled=True
     if s in regs:
      mem[dst_slot]=regs[s];st['spill_seen']=True
      spills.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'spill_site':f'0x{a:08x}',
                     'stack_base':dst_slot[0],'stack_displacement':dst_slot[1],'source_register':s,
                     'transformed':regs[s],'distance':st['age']})
     else:mem.pop(dst_slot,None)
    elif d in REGS and src_slot:
     handled=True
     if src_slot in mem:
      regs[d]=mem[src_slot];st['reload_seen']=True
      reloads.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'reload_site':f'0x{a:08x}',
                      'stack_base':src_slot[0],'stack_displacement':src_slot[1],'destination_register':d,
                      'transformed':mem[src_slot],'distance':st['age']})
     else:regs.pop(d,None)
    elif d in REGS and s in REGS:
     handled=True
     if s in regs:regs[d]=regs[s]
     else:regs.pop(d,None)
   if not handled and mn=='xchg' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
    handled=True;d,s=parts;dv=regs.pop(d,None);sv=regs.pop(s,None)
    if dv is not None:regs[s]=dv
    if sv is not None:regs[d]=sv
   if not handled and mn in DEST_DEP and parts and parts[0] in REGS:
    handled=True;d=parts[0]
    if d in regs:
     erase=(len(parts)>=2 and parts[1]==d and mn in {'xor','sub'}) or (len(parts)>=2 and parts[1] in {'0','0x0'} and mn=='and')
     if erase:regs.pop(d,None)
     else:regs[d]=True
    elif writes_reg(mn,ops,d):regs.pop(d,None)
   if not handled and mn=='imul' and len(parts)>=2 and parts[0] in REGS:
    handled=True;d,s=parts[0],parts[1]
    if s in regs:regs[d]=True
    else:regs.pop(d,None)
   if not handled and mn=='lea' and len(parts)==2 and parts[0] in REGS:
    handled=True;d,s=parts
    src=[r for r in REGS if re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',s) and r in regs]
    if src:regs[d]=True
    else:regs.pop(d,None)
   if not handled:
    if parts:
     dst_slot=stack_slot(parts[0])
     if dst_slot and mn not in READ_ONLY_FIRST:mem.pop(dst_slot,None)
    for r in list(regs):
     if writes_reg(mn,ops,r):regs.pop(r,None)
   if inv_ebp:mem={k:v for k,v in mem.items() if k[0]!='ebp'}
   if inv_esp:mem={k:v for k,v in mem.items() if k[0]!='esp'}
   if not regs and not mem:terms['all_taint_dead']+=1;continue
   if st['age']>=WINDOW:terms['window_exhausted']+=1;continue
   st['regs']=regs;st['mem']=mem;new.append(st)
  active=new
  q=parse_load(mn,ops)
  if q:
   reg,slot=q;loads+=1;slots.add(slot);active.append({'load':a,'slot':slot,'regs':{reg:False},'mem':{},'age':0,'spill_seen':False,'reload_seen':False})
 reload_hits=[x for x in hits if x['reload_seen']]
 spill_by=Counter(x['stack_base'] for x in spills);reload_by=Counter(x['stack_base'] for x in reloads)
 return {
  'decoded_instruction_count':inst,'absolute_data_load_count':loads,'unique_absolute_data_slot_count':len(slots),
  'stack_spill_event_count':len(spills),'spilled_load_count':len({x['load_site'] for x in spills}),
  'stack_spill_count_by_base':dict(sorted(spill_by.items())),'transformed_stack_spill_count':sum(bool(x['transformed']) for x in spills),
  'stack_reload_event_count':len(reloads),'reloaded_load_count':len({x['load_site'] for x in reloads}),
  'stack_reload_count_by_base':dict(sorted(reload_by.items())),'transformed_stack_reload_count':sum(bool(x['transformed']) for x in reloads),
  'reload_events':reloads,'spill_event_samples':spills[:8]+spills[-4:] if len(spills)>12 else spills,
  'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,
  'reload_derived_indirect_transfer_count':len(reload_hits),'reload_derived_indirect_transfers':reload_hits,
  'termination_reason_counts':dict(sorted(terms.items()))
 }

def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up['adjudication'].get('p13a_fun005ffc50_absolute_data_transform_near_transfer_subset_complete'):raise AssertionError('upstream transform subset incomplete')
 if up['inventory']['absolute_data_load_count']!=1786 or up['inventory']['transform_event_count']!=179:raise AssertionError('upstream inventory drift')
 r=scan_rows(dis(exe))
 if r['decoded_instruction_count']!=2847850 or r['absolute_data_load_count']!=1786 or r['unique_absolute_data_slot_count']!=434:raise AssertionError(('retail inventory drift',r))
 expected_spill_base={'ebp':91,'esp':18};expected_reload_base={'ebp':8}
 if r['stack_spill_event_count']!=109 or r['spilled_load_count']!=108 or r['stack_spill_count_by_base']!=expected_spill_base or r['transformed_stack_spill_count']!=82:raise AssertionError(('spill inventory drift',r))
 if r['stack_reload_event_count']!=8 or r['reloaded_load_count']!=8 or r['stack_reload_count_by_base']!=expected_reload_base or r['transformed_stack_reload_count']!=0:raise AssertionError(('reload inventory drift',r))
 if r['tainted_register_indirect_transfer_count'] or r['reload_derived_indirect_transfer_count']:raise AssertionError(('unexpected transfer',r['tainted_register_indirect_transfers']))
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},
  'scope':{'data_start':f'0x{DATA_START:08x}','data_end_exclusive':f'0x{DATA_END:08x}','forward_window_decoded_instructions':WINDOW,
           'stack_slot_shape':'exact DWORD PTR [ebp/esp +/- immediate] mov spill/reload',
           'stack_base_invalidation':['any write to EBP invalidates EBP-relative tracked slots','push/pop or write to ESP invalidates ESP-relative tracked slots'],
           'implicit_push_pop_taint_tracking':False,
           'stops_on':['any call/jmp after transfer check','conditional branch/loop/ret/trap','all register and tracked-stack taint dead','16-instruction window']},
  'inventory':r,
  'adjudication':{
   'p13a_fun005ffc50_absolute_data_stack_spill_reload_subset_complete':True,
   'absolute_data_stack_reload_indirect_transfer_found':False,
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
   'This closes exact mov-based EBP/ESP-relative stack spill/reload within the same 16-instruction straight-line window while preserving the upstream GPR copy/transform taint.',
   'Implicit push/pop value transfer, stack-pointer-delta normalization across ESP changes, memory aliases, inter-block carry, base/indexed writable sources, heap/runtime values and return provenance remain open.',
   'Retail has 109 tracked spills and 8 exact reloads; none of the reload-derived values reaches an indirect call/jmp.',
   'No global writable-memory, callback, reconstructed-entry, slot0, slot1, stored-alias or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Trace inter-block carry and implicit/normalized stack transfer, then base/indexed writable-memory and alias sources; exact same-block mov spill/reload is now negative.'
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
