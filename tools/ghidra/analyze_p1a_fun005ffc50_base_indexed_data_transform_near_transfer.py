#!/usr/bin/env python3
"""Bound copy/transform propagation from base/index-addressed writable .data loads."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, re, subprocess
from collections import Counter
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataTransformNearTransfer/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataNearTransfer/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
DATA_START,DATA_END=0x00b81000,0x00bbc600
WINDOW=16
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
MEM=re.compile(r'^(?:DWORD PTR )?\[([^\]]+)\]$')
IMM=re.compile(r'^(?:0x([0-9a-fA-F]+)|([0-9]+))$')
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
def scan_rows(rows):
 rows=list(rows);addr_state={};active=[];loads=[];copies=[];events=[];hits=[];terms=Counter()
 for a,mn,ops in rows:
  parts=ops.split(',') if ops else [];new=[]
  for st in active:
   st['age']+=1
   if mn in {'call','jmp'}:
    if ops in st['regs']:
     hits.append({'load_site':f"0x{st['load']:08x}",'effective_address':f"0x{st['ea']:08x}",'transfer_site':f'0x{a:08x}','kind':mn,'transfer_register':ops,'distance':st['age'],'transformed':st['regs'][ops]})
     terms['matched_transfer']+=1
    else:terms['other_control_transfer']+=1
    continue
   if mn.startswith('j') or mn.startswith('loop') or mn in CONTROL_STOPS or mn in {'ret','retn'}:
    terms['other_control_transfer']+=1;continue
   regs=dict(st['regs']);copy=None;event=None
   if mn=='mov' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
    d,s=parts
    if s in regs:regs[d]=regs[s];copy=(d,s)
    else:regs.pop(d,None)
   elif mn=='xchg' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
    d,s=parts;dv=regs.pop(d,None);sv=regs.pop(s,None)
    if dv is not None:regs[s]=dv;copy=(s,d)
    if sv is not None:regs[d]=sv;copy=(d,s)
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
    d,s=parts;src=[r for r in REGS if re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',s) and r in regs]
    if src:regs[d]=True;event=(mn,d)
    else:regs.pop(d,None)
   else:
    for r in list(regs):
     if writes_reg(mn,ops,r):regs.pop(r,None)
   if copy:copies.append({'load_site':f"0x{st['load']:08x}",'copy_site':f'0x{a:08x}','destination_register':copy[0],'source_register':copy[1],'distance':st['age']})
   if event:events.append({'load_site':f"0x{st['load']:08x}",'transform_site':f'0x{a:08x}','mnemonic':event[0],'instruction':f'{mn} {ops}'.rstrip(),'destination_register':event[1],'distance':st['age']})
   if not regs:terms['all_tainted_registers_clobbered']+=1;continue
   if st['age']>=WINDOW:terms['window_exhausted']+=1;continue
   st['regs']=regs;new.append(st)
  active=new
  q=parse_load(mn,ops,state_values(addr_state))
  if q:
   reg,ea,src=q;loads.append((a,reg,ea,src));active.append({'load':a,'ea':ea,'regs':{reg:False},'age':0})
  addr_state=update_state(mn,ops,addr_state)
 transformed_hits=[x for x in hits if x['transformed']]
 return {'decoded_instruction_count':len(rows),'base_indexed_data_load_count':len(loads),'unique_effective_address_count':len({x[2] for x in loads}),'copy_event_count':len(copies),'copied_load_count':len({x['load_site'] for x in copies}),'unique_copy_site_count':len({x['copy_site'] for x in copies}),'copy_event_samples':copies,'transform_event_count':len(events),'transformed_load_count':len({x['load_site'] for x in events}),'unique_transform_site_count':len({x['transform_site'] for x in events}),'transform_count_by_mnemonic':dict(sorted(Counter(x['mnemonic'] for x in events).items())),'transform_event_samples':events,'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,'transformed_register_indirect_transfer_count':len(transformed_hits),'transformed_register_indirect_transfers':transformed_hits,'termination_reason_counts':dict(sorted(terms.items()))}
def analyze(exe,upstream):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up['adjudication'].get('p13a_fun005ffc50_base_indexed_data_same_register_near_transfer_subset_complete'):raise AssertionError('upstream incomplete')
 r=scan_rows(dis(exe))
 if (r['decoded_instruction_count'],r['base_indexed_data_load_count'],r['unique_effective_address_count'])!=(2847850,63,51):raise AssertionError(('inventory drift',r))
 if (r['copy_event_count'],r['copied_load_count'],r['unique_copy_site_count'])!=(1,1,1):raise AssertionError(('copy drift',r))
 if (r['transform_event_count'],r['transformed_load_count'],r['unique_transform_site_count'])!=(4,3,4):raise AssertionError(('transform drift',r))
 if r['transform_count_by_mnemonic']!={'add':1,'and':1,'imul':1,'sar':1}:raise AssertionError(('transform mix drift',r))
 if r['tainted_register_indirect_transfer_count'] or r['transformed_register_indirect_transfer_count']:raise AssertionError(('unexpected transfer',r))
 if r['termination_reason_counts']!={'all_tainted_registers_clobbered':4,'other_control_transfer':59}:raise AssertionError(('termination drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'forward_window_decoded_instructions':WINDOW,'address_source_model':'same bounded exact base/index model as upstream','identity_copy_ops':['mov GPR,GPR','xchg GPR,GPR'],'dependency_preserving_transform_ops':sorted(DEST_DEP|{'imul','lea'}),'dependency_erasing_special_cases':['xor reg,reg','sub reg,reg','and reg,0'],'stops_on':['any call/jmp after transfer check','conditional branch/loop/ret/trap','clobber of every tainted GPR','16-instruction window']},'inventory':r,'adjudication':{'p13a_fun005ffc50_base_indexed_data_copy_transform_near_transfer_subset_complete':True,'base_indexed_data_copied_or_transformed_register_indirect_transfer_found':False,'base_indexed_stack_spill_reload_ruled_out':False,'base_indexed_inter_block_carry_ruled_out':False,'base_indexed_writable_sources_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes only same-window GPR copies and selected dependency-preserving arithmetic/bitwise/shift/LEA transforms from the 63 upstream base/index-addressed writable .data loads.','Stack spill/reload, memory aliases, inter-block/phi carry, runtime/heap values and aggregate P1.3 gates remain open.'],'next_step':'Trace stack spill/reload and bounded inter-block carry for base/index-derived writable .data provenance.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
