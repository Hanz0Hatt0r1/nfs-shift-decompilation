#!/usr/bin/env python3
"""Bound implicit push/pop transfer of writable .data-derived GPR taint."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50AbsoluteDataImplicitPushPop/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50AbsoluteDataStackSpillReload/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
DATA_START,DATA_END=0x00b81000,0x00bbc600
WINDOW=16
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
ABS_LOAD=re.compile(r'^(?:(DWORD PTR )?ds:)0x([0-9a-fA-F]+)$')
READ_ONLY_FIRST={'cmp','test','push','call','jmp','bt','btc','btr','bts','nop'}
CONTROL_STOPS={'int','int3','ud2','iret','iretd'}
DEST_DEP={'add','sub','xor','or','and','adc','sbb','shl','sal','shr','sar','rol','ror','rcl','rcr','inc','dec','neg','not'}
PUSH_UNKNOWN={'pushf','pushfd','pusha','pushad'}
POP_UNKNOWN={'popf','popfd','popa','popad'}
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe:Path):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout
 for line in p.stdout:
  m=I.match(line)
  if m:yield int(m.group(1),16),m.group(2).lower(),norm(m.group(3))
 err=p.stderr.read() if p.stderr else ''
 if p.wait():raise RuntimeError(err)
def parse_load(mn,ops):
 if mn!='mov' or ',' not in ops:return None
 d,s=ops.split(',',1)
 if d not in REGS:return None
 q=ABS_LOAD.fullmatch(s)
 if q:
  a=int(q.group(2),16)
  if DATA_START<=a<DATA_END:return d,a
def writes_reg(mn,ops,reg):
 p=ops.split(',') if ops else []
 if mn=='xchg' and any(x==reg or SUB.get(x)==reg for x in p):return True
 if p and mn not in READ_ONLY_FIRST:
  d=p[0]
  if d==reg or SUB.get(d)==reg:return True
 if reg in {'eax','edx'} and mn in {'mul','div','idiv','cdq','cwd','cwde'}:return True
 if reg in {'eax','edx'} and mn=='imul' and len(p)==1:return True
 return False
def scan_rows(rows):
 active=[];pushes=[];pops=[];hits=[];terms=Counter();loads=0;slots=set();inst=0
 for a,mn,ops in rows:
  inst+=1;p=ops.split(',') if ops else [];new=[]
  for st in active:
   st['age']+=1
   if mn in {'call','jmp'}:
    if ops in st['regs']:
     hits.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'transfer_site':f'0x{a:08x}','kind':mn,
                  'transfer_register':ops,'distance':st['age'],'transformed':st['regs'][ops],'pop_seen':st['pop_seen']})
     terms['matched_transfer']+=1
    else:terms['other_control_transfer']+=1
    continue
   if mn.startswith('j') or mn.startswith('loop') or mn in CONTROL_STOPS or mn in {'ret','retn'}:
    terms['other_control_transfer']+=1;continue
   regs=dict(st['regs']);stack=list(st['stack']);handled=False
   if mn=='push':
    handled=True;flag=regs.get(ops) if ops in regs else None;stack.append(flag)
    if flag is not None:
     st['push_seen']=True;pushes.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'push_site':f'0x{a:08x}',
                                        'source_register':ops,'transformed':flag,'distance':st['age']})
   elif mn=='pop':
    handled=True;flag=stack.pop() if stack else None
    if ops in REGS:
     if flag is None:regs.pop(ops,None)
     else:
      regs[ops]=flag;st['pop_seen']=True;pops.append({'load_site':f"0x{st['load']:08x}",'slot':f"0x{st['slot']:08x}",'pop_site':f'0x{a:08x}',
                                                     'destination_register':ops,'transformed':flag,'distance':st['age']})
   elif mn in PUSH_UNKNOWN:
    handled=True;stack.append(None)
   elif mn in POP_UNKNOWN:
    handled=True
    if stack:stack.pop()
   elif p and p[0] in {'esp','sp'}:
    terms['unmodelled_esp_write']+=1;continue
   elif mn=='mov' and len(p)==2 and p[0] in REGS and p[1] in REGS:
    handled=True;d,s=p
    if s in regs:regs[d]=regs[s]
    else:regs.pop(d,None)
   elif mn=='xchg' and len(p)==2 and p[0] in REGS and p[1] in REGS:
    handled=True;d,s=p;dv=regs.pop(d,None);sv=regs.pop(s,None)
    if dv is not None:regs[s]=dv
    if sv is not None:regs[d]=sv
   elif mn in DEST_DEP and p and p[0] in REGS:
    handled=True;d=p[0]
    if d in regs:
     erase=(len(p)>=2 and p[1]==d and mn in {'xor','sub'}) or (len(p)>=2 and p[1] in {'0','0x0'} and mn=='and')
     if erase:regs.pop(d,None)
     else:regs[d]=True
    elif writes_reg(mn,ops,d):regs.pop(d,None)
   elif mn=='imul' and len(p)>=2 and p[0] in REGS:
    handled=True;d,s=p[0],p[1]
    if s in regs:regs[d]=True
    else:regs.pop(d,None)
   elif mn=='lea' and len(p)==2 and p[0] in REGS:
    handled=True;d,s=p;src=[r for r in REGS if re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',s) and r in regs]
    if src:regs[d]=True
    else:regs.pop(d,None)
   if not handled:
    for r in list(regs):
     if writes_reg(mn,ops,r):regs.pop(r,None)
   if not regs and not any(x is not None for x in stack):terms['all_taint_dead']+=1;continue
   if st['age']>=WINDOW:terms['window_exhausted']+=1;continue
   st['regs']=regs;st['stack']=stack;new.append(st)
  active=new
  q=parse_load(mn,ops)
  if q:
   reg,slot=q;loads+=1;slots.add(slot);active.append({'load':a,'slot':slot,'regs':{reg:False},'stack':[],'age':0,'push_seen':False,'pop_seen':False})
 pop_hits=[x for x in hits if x['pop_seen']]
 return {'decoded_instruction_count':inst,'absolute_data_load_count':loads,'unique_absolute_data_slot_count':len(slots),
         'tainted_push_event_count':len(pushes),'pushed_load_count':len({x['load_site'] for x in pushes}),
         'push_count_by_register':dict(sorted(Counter(x['source_register'] for x in pushes).items())),
         'transformed_tainted_push_count':sum(bool(x['transformed']) for x in pushes),
         'tainted_pop_reload_event_count':len(pops),'popped_load_count':len({x['load_site'] for x in pops}),
         'pop_reload_events':pops,'push_event_samples':pushes[:8]+pushes[-4:] if len(pushes)>12 else pushes,
         'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,
         'pop_derived_indirect_transfer_count':len(pop_hits),'pop_derived_indirect_transfers':pop_hits,
         'termination_reason_counts':dict(sorted(terms.items()))}
def analyze(exe,upstream):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up['adjudication'].get('p13a_fun005ffc50_absolute_data_stack_spill_reload_subset_complete'):raise AssertionError('upstream stack subset incomplete')
 r=scan_rows(dis(exe));expected_push={'eax':92,'ecx':71,'edx':44,'esi':1}
 if r['decoded_instruction_count']!=2847850 or r['absolute_data_load_count']!=1786 or r['unique_absolute_data_slot_count']!=434:raise AssertionError(('inventory drift',r))
 if r['tainted_push_event_count']!=208 or r['pushed_load_count']!=208 or r['push_count_by_register']!=expected_push or r['transformed_tainted_push_count']!=12:raise AssertionError(('push drift',r))
 if r['tainted_pop_reload_event_count'] or r['pop_derived_indirect_transfer_count'] or r['tainted_register_indirect_transfer_count']:raise AssertionError(('unexpected pop/transfer',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},
  'scope':{'data_start':f'0x{DATA_START:08x}','data_end_exclusive':f'0x{DATA_END:08x}','forward_window_decoded_instructions':WINDOW,
           'implicit_stack_model':'push creates one abstract stack cell; pop consumes top cell; nested push/pop allowed',
           'unmodelled_esp_write_policy':'stop provenance on arithmetic/LEA/other writes to ESP or SP',
           'explicit_stack_spill_reload_composed_upstream':True},
  'inventory':r,
  'adjudication':{'p13a_fun005ffc50_absolute_data_implicit_push_pop_subset_complete':True,'absolute_data_implicit_pop_indirect_transfer_found':False,
   'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
   'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'return_value_fun005ffc50_provenance_ruled_out':False,
   'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,'encoded_or_reconstructed_callback_entry_ruled_out':False,
   'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,
   'fun0067b660_callback_argument_provenance_complete':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
   'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['This closes only implicit push/pop value transfer for GPR taint derived directly from absolute .data loads plus bounded same-block copies/transforms.',
            'Arbitrary ESP arithmetic/LEA normalization, explicit stack aliases beyond the separate upstream mov spill/reload contract, inter-block carry, base/indexed writable sources, heap/runtime values and return provenance remain open.',
            'Retail contains 208 tainted pushes but zero tainted pop reloads before the bounded control-flow/window boundary, hence zero pop-derived indirect transfers.',
            'No global writable-memory, callback, reconstructed-entry, slot0, slot1, stored-alias or aggregate P1.3 gate is promoted.'],
  'next_step':'Normalize simple ESP arithmetic and then trace inter-block/base-indexed writable-memory provenance; implicit push/pop transfer is now bounded.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
