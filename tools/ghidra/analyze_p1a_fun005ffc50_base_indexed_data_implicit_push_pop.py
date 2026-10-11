#!/usr/bin/env python3
"""Bound implicit push/pop from base/index-addressed writable .data-derived GPR taint."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataImplicitPushPop/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataStackSpillReload/1'
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
PUSH_UNKNOWN={'pushf','pushfd','pusha','pushad'}
POP_UNKNOWN={'popf','popfd','popa','popad'}
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
 rows=list(rows);addr_state={};active=[];loads=[];pushes=[];pops=[];hits=[];terms=Counter()
 for a,mn,ops in rows:
  p=ops.split(',') if ops else [];new=[]
  for st in active:
   st['age']+=1
   if mn in {'call','jmp'}:
    if ops in st['regs']:
     hits.append({'load_site':f"0x{st['load']:08x}",'effective_address':f"0x{st['ea']:08x}",'transfer_site':f'0x{a:08x}','kind':mn,'transfer_register':ops,'distance':st['age'],'transformed':st['regs'][ops],'pop_seen':st['pop_seen']})
     terms['matched_transfer']+=1
    else:terms['other_control_transfer']+=1
    continue
   if mn.startswith('j') or mn.startswith('loop') or mn in CONTROL_STOPS or mn in {'ret','retn'}:
    terms['other_control_transfer']+=1;continue
   regs=dict(st['regs']);stack=list(st['stack']);handled=False
   if mn=='push':
    handled=True;flag=regs.get(ops) if ops in regs else None;stack.append(flag)
    if flag is not None:
     pushes.append({'load_site':f"0x{st['load']:08x}",'effective_address':f"0x{st['ea']:08x}",'push_site':f'0x{a:08x}','source_register':ops,'transformed':flag,'distance':st['age']})
   elif mn=='pop':
    handled=True;flag=stack.pop() if stack else None
    if ops in REGS:
     if flag is None:regs.pop(ops,None)
     else:
      regs[ops]=flag;st['pop_seen']=True;pops.append({'load_site':f"0x{st['load']:08x}",'effective_address':f"0x{st['ea']:08x}",'pop_site':f'0x{a:08x}','destination_register':ops,'transformed':flag,'distance':st['age']})
   elif mn in PUSH_UNKNOWN:
    handled=True;stack.append(None)
   elif mn in POP_UNKNOWN:
    handled=True
    if stack:stack.pop()
   elif p and p[0] in {'esp','sp'}:
    terms['unmodelled_esp_write']+=1;continue
   elif mn=='mov' and len(p)==2 and p[0] in REGS and p[1] in REGS:
    handled=True;d,src=p
    if src in regs:regs[d]=regs[src]
    else:regs.pop(d,None)
   elif mn=='xchg' and len(p)==2 and p[0] in REGS and p[1] in REGS:
    handled=True;d,src=p;dv=regs.pop(d,None);sv=regs.pop(src,None)
    if dv is not None:regs[src]=dv
    if sv is not None:regs[d]=sv
   elif mn in DEST_DEP and p and p[0] in REGS:
    handled=True;d=p[0]
    if d in regs:
     erase=(len(p)>=2 and p[1]==d and mn in {'xor','sub'}) or (len(p)>=2 and p[1] in {'0','0x0'} and mn=='and')
     if erase:regs.pop(d,None)
     else:regs[d]=True
    elif writes_reg(mn,ops,d):regs.pop(d,None)
   elif mn=='imul' and len(p)>=2 and p[0] in REGS:
    handled=True;d,src=p[0],p[1]
    if src in regs:regs[d]=True
    else:regs.pop(d,None)
   elif mn=='lea' and len(p)==2 and p[0] in REGS:
    handled=True;d,src=p;refs=[r for r in REGS if re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',src) and r in regs]
    if refs:regs[d]=True
    else:regs.pop(d,None)
   if not handled:
    for r in list(regs):
     if writes_reg(mn,ops,r):regs.pop(r,None)
   if not regs and not any(x is not None for x in stack):terms['all_taint_dead']+=1;continue
   if st['age']>=WINDOW:terms['window_exhausted']+=1;continue
   st['regs']=regs;st['stack']=stack;new.append(st)
  active=new
  q=parse_load(mn,ops,state_values(addr_state))
  if q:
   reg,ea,src=q;loads.append((a,reg,ea,src));active.append({'load':a,'ea':ea,'regs':{reg:False},'stack':[],'age':0,'pop_seen':False})
  addr_state=update_state(mn,ops,addr_state)
 pop_hits=[x for x in hits if x['pop_seen']]
 return {'decoded_instruction_count':len(rows),'base_indexed_data_load_count':len(loads),'unique_effective_address_count':len({x[2] for x in loads}),'tainted_push_event_count':len(pushes),'pushed_load_count':len({x['load_site'] for x in pushes}),'push_count_by_register':dict(sorted(Counter(x['source_register'] for x in pushes).items())),'transformed_tainted_push_count':sum(bool(x['transformed']) for x in pushes),'tainted_pop_reload_event_count':len(pops),'popped_load_count':len({x['load_site'] for x in pops}),'push_events':pushes,'pop_reload_events':pops,'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':hits,'pop_derived_indirect_transfer_count':len(pop_hits),'pop_derived_indirect_transfers':pop_hits,'termination_reason_counts':dict(sorted(terms.items()))}
def analyze(exe,upstream):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text())
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up['adjudication'].get('p13a_fun005ffc50_base_indexed_data_stack_spill_reload_subset_complete'):raise AssertionError('upstream incomplete')
 r=scan_rows(dis(exe))
 if (r['decoded_instruction_count'],r['base_indexed_data_load_count'],r['unique_effective_address_count'])!=(2847850,63,51):raise AssertionError(('inventory drift',r))
 if (r['tainted_push_event_count'],r['pushed_load_count'],r['push_count_by_register'],r['transformed_tainted_push_count'])!=(5,5,{'eax':3,'ecx':2},0):raise AssertionError(('push drift',r))
 if r['tainted_pop_reload_event_count'] or r['popped_load_count'] or r['pop_derived_indirect_transfer_count'] or r['tainted_register_indirect_transfer_count']:raise AssertionError(('unexpected pop/transfer',r))
 if r['termination_reason_counts']!={'all_taint_dead':2,'other_control_transfer':61}:raise AssertionError(('termination drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'forward_window_decoded_instructions':WINDOW,'address_source_model':'same bounded exact base/index model as upstream','implicit_stack_model':'push creates one abstract stack cell; pop consumes top cell; nested push/pop allowed','unmodelled_esp_write_policy':'stop provenance on arithmetic/LEA/other writes to ESP or SP','explicit_stack_spill_reload_composed_upstream':True},'inventory':r,'adjudication':{'p13a_fun005ffc50_base_indexed_data_implicit_push_pop_subset_complete':True,'base_indexed_data_implicit_pop_indirect_transfer_found':False,'base_indexed_esp_normalization_ruled_out':False,'base_indexed_inter_block_carry_ruled_out':False,'base_indexed_writable_sources_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes only implicit push/pop value transfer for base/index-derived GPR taint plus bounded same-window copies/transforms.','Simple ESP arithmetic/LEA normalization, broader explicit stack aliases, inter-block/phi carry, runtime/heap values and aggregate P1.3 gates remain open.'],'next_step':'Normalize simple ESP arithmetic/LEA for base/index-derived taint, then trace bounded inter-block carry.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
