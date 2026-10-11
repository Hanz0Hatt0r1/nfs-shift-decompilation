#!/usr/bin/env python3
"""Bound exact EBP/ESP stack spill/reload from base/index-addressed writable .data loads."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataStackSpillReload/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataTransformNearTransfer/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
DATA_START,DATA_END=0x00b81000,0x00bbc600
WINDOW=16
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
MEM=re.compile(r'^(?:DWORD PTR )?\[([^\]]+)\]$')
IMM=re.compile(r'^(?:0x([0-9a-fA-F]+)|([0-9]+))$')
STACK_SLOT=re.compile(r'^(?:DWORD PTR )?\[(ebp|esp)([+-]0x[0-9a-fA-F]+)?\]$')
READ_ONLY_FIRST={'cmp','test','push','call','jmp','bt','btc','btr','bts','nop'}
CONTROL_STOPS={'int','int3','ud2','iret','iretd'}
DEST_DEP={'add','sub','xor','or','and','adc','sbb','shl','sal','shr','sar','rol','ror','rcl','rcr','inc','dec','neg','not'}
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe:Path):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout
 for line in p.stdout:
  m=I.match(line)
  if m:yield int(m.group(1),16),m.group(2).lower(),norm(m.group(3))
 err=p.stderr.read() if p.stderr else ''
 if p.wait():raise RuntimeError(err)
def parse_imm(s):
 m=IMM.fullmatch(s)
 if not m:return None
 return int(m.group(1),16) if m.group(1) else int(m.group(2),10)
def split_terms(expr):return re.findall(r'[+-]?[^+-]+',expr.replace(' ',''))
def eval_expr(expr,consts):
 total=0;used=False
 for raw in split_terms(expr):
  sign=-1 if raw.startswith('-') else 1;t=raw[1:] if raw[:1] in '+-' else raw
  if '*' in t:
   r,sc=t.split('*',1)
   if r not in REGS or r not in consts:return None
   n=parse_imm(sc)
   if n is None:return None
   total+=sign*consts[r]*n;used=True
  elif t in REGS:
   if t not in consts:return None
   total+=sign*consts[t];used=True
  else:
   n=parse_imm(t)
   if n is None:return None
   total+=sign*n
 return (total&0xffffffff) if used else None
def writes_reg(mn,ops,reg):
 p=ops.split(',') if ops else []
 if mn=='xchg' and any(x==reg or SUB.get(x)==reg for x in p):return True
 if p and mn not in READ_ONLY_FIRST:
  d=p[0]
  if d==reg or SUB.get(d)==reg:return True
 if reg in {'eax','edx'} and mn in {'mul','div','idiv','cdq','cwd','cwde'}:return True
 if reg in {'eax','edx'} and mn=='imul' and len(p)==1:return True
 return False
def state_values(state):return {r:v for r,(v,age) in state.items() if age<=WINDOW}
def update_state(mn,ops,state):
 p=ops.split(',') if ops else [];c={r:(v,age+1) for r,(v,age) in state.items() if age+1<=WINDOW}
 if mn=='call':return {r:x for r,x in c.items() if r in {'ebx','esi','edi','ebp'}}
 if mn in {'jmp','ret','retn'} or mn.startswith('j') or mn.startswith('loop') or mn in CONTROL_STOPS:return {}
 if mn=='mov' and len(p)==2 and p[0] in REGS:
  d,s=p;n=parse_imm(s)
  if n is not None:c[d]=(n&0xffffffff,0)
  elif s in c:c[d]=(c[s][0],0)
  else:c.pop(d,None)
 elif mn=='lea' and len(p)==2 and p[0] in REGS:
  d,s=p;q=MEM.fullmatch(s);v=eval_expr(q.group(1),state_values(c)) if q else None
  if v is None:c.pop(d,None)
  else:c[d]=(v,0)
 elif mn in {'add','sub'} and len(p)==2 and p[0] in REGS:
  d,s=p;n=parse_imm(s)
  if d in c and n is not None:c[d]=((c[d][0]+(n if mn=='add' else -n))&0xffffffff,0)
  else:c.pop(d,None)
 elif mn=='xor' and len(p)==2 and p[0] in REGS and p[0]==p[1]:c[p[0]]=(0,0)
 else:
  for r in REGS:
   if writes_reg(mn,ops,r):c.pop(r,None)
 return c
def parse_load(mn,ops,consts):
 if mn!='mov' or ',' not in ops:return None
 d,s=ops.split(',',1)
 if d not in REGS:return None
 q=MEM.fullmatch(s)
 if not q:return None
 ea=eval_expr(q.group(1),consts)
 if ea is not None and DATA_START<=ea<DATA_END:return d,ea,s
def stack_slot(op):
 m=STACK_SLOT.fullmatch(op)
 if not m:return None
 return m.group(1),m.group(2) or '+0x0'
def invalidates_stack_base(mn,ops,base):
 p=ops.split(',') if ops else []
 if base=='esp' and mn in {'push','pop','pushf','popf','pusha','popa','enter','leave'}:return True
 aliases={'esp','sp'} if base=='esp' else {'ebp','bp'}
 return bool(p and p[0] in aliases and mn not in READ_ONLY_FIRST)
def scan_rows(rows):
 rows=list(rows);addr_state={};active=[];loads=[];spills=[];reloads=[];hits=[];terms=Counter()
 for a,mn,ops in rows:
  parts=ops.split(',') if ops else [];new=[]
  for st in active:
   st['age']+=1
   if mn in {'call','jmp'}:
    if ops in st['regs']:
     hits.append({'load_site':f"0x{st['load']:08x}",'effective_address':f"0x{st['ea']:08x}",'transfer_site':f'0x{a:08x}','kind':mn,'transfer_register':ops,'distance':st['age'],'transformed':st['regs'][ops],'reload_seen':st['reload_seen']})
     terms['matched_transfer']+=1
    else:terms['other_control_transfer']+=1
    continue
   if mn.startswith('j') or mn.startswith('loop') or mn in CONTROL_STOPS or mn in {'ret','retn'}:
    terms['other_control_transfer']+=1;continue
   regs=dict(st['regs']);mem=dict(st['mem']);handled=False
   inv_ebp=invalidates_stack_base(mn,ops,'ebp');inv_esp=invalidates_stack_base(mn,ops,'esp')
   if mn=='mov' and len(parts)==2:
    d,src=parts;dst_slot=stack_slot(d);src_slot=stack_slot(src)
    if dst_slot and src in REGS:
     handled=True
     if src in regs:
      mem[dst_slot]=regs[src];spills.append({'load_site':f"0x{st['load']:08x}",'effective_address':f"0x{st['ea']:08x}",'spill_site':f'0x{a:08x}','stack_base':dst_slot[0],'stack_displacement':dst_slot[1],'source_register':src,'transformed':regs[src],'distance':st['age']})
     else:mem.pop(dst_slot,None)
    elif d in REGS and src_slot:
     handled=True
     if src_slot in mem:
      regs[d]=mem[src_slot];st['reload_seen']=True;reloads.append({'load_site':f"0x{st['load']:08x}",'effective_address':f"0x{st['ea']:08x}",'reload_site':f'0x{a:08x}','stack_base':src_slot[0],'stack_displacement':src_slot[1],'destination_register':d,'transformed':mem[src_slot],'distance':st['age']})
     else:regs.pop(d,None)
    elif d in REGS and src in REGS:
     handled=True
     if src in regs:regs[d]=regs[src]
     else:regs.pop(d,None)
   if not handled and mn=='xchg' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
    handled=True;d,src=parts;dv=regs.pop(d,None);sv=regs.pop(src,None)
    if dv is not None:regs[src]=dv
    if sv is not None:regs[d]=sv
   if not handled and mn in DEST_DEP and parts and parts[0] in REGS:
    handled=True;d=parts[0]
    if d in regs:
     erase=(len(parts)>=2 and parts[1]==d and mn in {'xor','sub'}) or (len(parts)>=2 and parts[1] in {'0','0x0'} and mn=='and')
     if erase:regs.pop(d,None)
     else:regs[d]=True
    elif writes_reg(mn,ops,d):regs.pop(d,None)
   if not handled and mn=='imul' and len(parts)>=2 and parts[0] in REGS:
    handled=True;d,src=parts[0],parts[1]
    if src in regs:regs[d]=True
    else:regs.pop(d,None)
   if not handled and mn=='lea' and len(parts)==2 and parts[0] in REGS:
    handled=True;d,src=parts;refs=[r for r in REGS if re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',src) and r in regs]
    if refs:regs[d]=True
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
  q=parse_load(mn,ops,state_values(addr_state))
  if q:
   reg,ea,src=q;loads.append((a,reg,ea,src));active.append({'load':a,'ea':ea,'regs':{reg:False},'mem':{},'age':0,'reload_seen':False})
  addr_state=update_state(mn,ops,addr_state)
 reload_hits=[x for x in hits if x['reload_seen']]
 return {'decoded_instruction_count':len(rows),'base_indexed_data_load_count':len(loads),'unique_effective_address_count':len({x[2] for x in loads}),'stack_spill_event_count':len(spills),'spilled_load_count':len({x['load_site'] for x in spills}),'stack_spill_count_by_base':dict(sorted(Counter(x['stack_base'] for x in spills).items())),'transformed_stack_spill_count':sum(bool(x['transformed']) for x in spills),'stack_reload_event_count':len(reloads),'reloaded_load_count':len({x['load_site'] for x in reloads}),'stack_reload_count_by_base':dict(sorted(Counter(x['stack_base'] for x in reloads).items())),'transformed_stack_reload_count':sum(bool(x['transformed']) for x in reloads),'spill_events':spills,'reload_events':reloads,'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,'reload_derived_indirect_transfer_count':len(reload_hits),'reload_derived_indirect_transfers':reload_hits,'termination_reason_counts':dict(sorted(terms.items()))}
def analyze(exe,upstream):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up['adjudication'].get('p13a_fun005ffc50_base_indexed_data_copy_transform_near_transfer_subset_complete'):raise AssertionError('upstream incomplete')
 r=scan_rows(dis(exe))
 if (r['decoded_instruction_count'],r['base_indexed_data_load_count'],r['unique_effective_address_count'])!=(2847850,63,51):raise AssertionError(('inventory drift',r))
 if (r['stack_spill_event_count'],r['spilled_load_count'],r['stack_spill_count_by_base'],r['transformed_stack_spill_count'])!=(2,2,{'ebp':1,'esp':1},1):raise AssertionError(('spill drift',r))
 if r['stack_reload_event_count'] or r['reloaded_load_count'] or r['stack_reload_count_by_base'] or r['transformed_stack_reload_count']:raise AssertionError(('reload drift',r))
 if r['tainted_register_indirect_transfer_count'] or r['reload_derived_indirect_transfer_count']:raise AssertionError(('unexpected transfer',r))
 if r['termination_reason_counts']!={'all_taint_dead':4,'other_control_transfer':59}:raise AssertionError(('termination drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'forward_window_decoded_instructions':WINDOW,'address_source_model':'same bounded exact base/index model as upstream','stack_slot_shape':'exact DWORD PTR [ebp/esp +/- immediate] mov spill/reload','stack_base_invalidation':['any write to EBP invalidates EBP-relative tracked slots','push/pop or write to ESP invalidates ESP-relative tracked slots'],'implicit_push_pop_taint_tracking':False,'stops_on':['any call/jmp after transfer check','conditional branch/loop/ret/trap','all register and tracked-stack taint dead','16-instruction window']},'inventory':r,'adjudication':{'p13a_fun005ffc50_base_indexed_data_stack_spill_reload_subset_complete':True,'base_indexed_data_stack_reload_indirect_transfer_found':False,'base_indexed_inter_block_carry_ruled_out':False,'base_indexed_writable_sources_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes exact mov-based EBP/ESP-relative stack spill/reload in the same 16-instruction window while preserving upstream GPR copy/transform taint.','Implicit push/pop, ESP-delta normalization for this base/index subset, memory aliases, inter-block/phi carry, runtime/heap values and aggregate P1.3 gates remain open.'],'next_step':'Trace implicit/normalized stack carriers and bounded inter-block carry for base/index-derived writable .data provenance.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
