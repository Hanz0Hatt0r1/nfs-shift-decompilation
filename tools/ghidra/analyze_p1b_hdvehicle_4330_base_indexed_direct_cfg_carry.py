#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'; DS,DE=0x00b81000,0x00bbc600; W=16
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
RO={'cmp','test','push','call','jmp','bt','btc','btr','bts','nop'}; DEP={'add','sub','xor','or','and','adc','sbb','shl','sal','shr','sar','rol','ror','rcl','rcr','inc','dec','neg','not'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$'); MEM=re.compile(r'^(?:DWORD PTR )?\[([^\]]+)\]$'); IMM=re.compile(r'^(?:0x([0-9a-fA-F]+)|([0-9]+))$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def imm(s):
 m=IMM.fullmatch(s);return None if not m else (int(m.group(1),16) if m.group(1) else int(m.group(2)))
def eval_expr(expr,c):
 total=0;used=False
 for raw in re.findall(r'[+-]?[^+-]+',expr.replace(' ','')):
  sign=-1 if raw.startswith('-') else 1;t=raw[1:] if raw[:1] in '+-' else raw
  if '*' in t:
   r,sc=t.split('*',1);n=imm(sc)
   if r not in REGS or r not in c or n is None:return None
   total+=sign*c[r]*n;used=True
  elif t in REGS:
   if t not in c:return None
   total+=sign*c[t];used=True
  else:
   n=imm(t)
   if n is None:return None
   total+=sign*n
 return (total&0xffffffff) if used else None
def writes(m,o,r):
 p=o.split(',') if o else []
 if m=='xchg' and any(x==r or SUB.get(x)==r for x in p):return True
 if p and m not in RO and (p[0]==r or SUB.get(p[0])==r):return True
 if r in {'eax','edx'} and m in {'mul','div','idiv','cdq','cwd','cwde'}:return True
 if r in {'eax','edx'} and m=='imul' and len(p)==1:return True
 return False
def update_consts(m,o,st):
 p=o.split(',') if o else [];c={r:(v,a+1) for r,(v,a) in st.items() if a+1<=W}
 if m=='call':return {r:x for r,x in c.items() if r in {'ebx','esi','edi','ebp'}}
 if m in {'jmp','ret','retn'} or m.startswith('j') or m.startswith('loop'):return {}
 if m=='mov' and len(p)==2 and p[0] in REGS:
  d,s=p;n=imm(s)
  if n is not None:c[d]=(n&0xffffffff,0)
  elif s in c:c[d]=(c[s][0],0)
  else:c.pop(d,None)
 elif m=='lea' and len(p)==2 and p[0] in REGS:
  d,s=p;q=MEM.fullmatch(s);v=eval_expr(q.group(1),{r:v for r,(v,a) in c.items()}) if q else None
  if v is None:c.pop(d,None)
  else:c[d]=(v,0)
 elif m in {'add','sub'} and len(p)==2 and p[0] in REGS:
  d,s=p;n=imm(s)
  if d in c and n is not None:c[d]=((c[d][0]+(n if m=='add' else -n))&0xffffffff,0)
  else:c.pop(d,None)
 elif m=='xor' and len(p)==2 and p[0]==p[1] and p[0] in REGS:c[p[0]]=(0,0)
 else:
  for r in REGS:
   if writes(m,o,r):c.pop(r,None)
 return c
def parse_load(m,o,c):
 if m!='mov' or ',' not in o:return None
 d,s=o.split(',',1)
 if d not in REGS:return None
 q=MEM.fullmatch(s)
 if not q:return None
 ea=eval_expr(q.group(1),c)
 return (d,ea) if ea is not None and DS<=ea<DE else None
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],text=True,capture_output=True,check=True,errors='replace');rows=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:rows.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return rows
def apply_taint(m,o,regs):
 p=o.split(',') if o else [];nr=dict(regs);handled=False
 if m=='mov' and len(p)==2 and p[0] in REGS and p[1] in REGS:
  handled=True;d,s=p
  if s in nr:nr[d]=nr[s]
  else:nr.pop(d,None)
 elif m=='mov' and len(p)==2 and p[0] in REGS:
  qmem=MEM.fullmatch(p[1]);handled=bool(qmem);d=p[0]
  if qmem:
   refs=[r for r in REGS if re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',qmem.group(1)) and r in nr]
   if refs:nr[d]=True
   else:nr.pop(d,None)
 elif m=='xchg' and len(p)==2 and p[0] in REGS and p[1] in REGS:
  handled=True;d,s=p;dv=nr.pop(d,None);sv=nr.pop(s,None)
  if dv is not None:nr[s]=dv
  if sv is not None:nr[d]=sv
 elif m in DEP and p and p[0] in REGS:
  handled=True;d=p[0]
  if d in nr:
   erase=(len(p)>=2 and p[1]==d and m in {'xor','sub'}) or (len(p)>=2 and p[1] in {'0','0x0'} and m=='and')
   if erase:nr.pop(d,None)
   else:nr[d]=True
  elif writes(m,o,d):nr.pop(d,None)
 elif m=='imul' and len(p)>=2 and p[0] in REGS:
  handled=True;d,s=p[0],p[1]
  if s in nr:nr[d]=True
  else:nr.pop(d,None)
 elif m=='lea' and len(p)==2 and p[0] in REGS:
  handled=True;d,s=p;refs=[r for r in REGS if re.search(r'(?<![a-z0-9])'+r+r'(?![a-z0-9])',s) and r in nr]
  if refs:nr[d]=True
  else:nr.pop(d,None)
 if not handled:
  for r in list(nr):
   if writes(m,o,r):nr.pop(r,None)
 return nr
def scan(rows):
 by={a:i for i,(a,_,_) in enumerate(rows)};const={};loads=[]
 for idx,(a,m,o) in enumerate(rows):
  q=parse_load(m,o,{r:v for r,(v,age) in const.items() if age<=W})
  if q:loads.append((idx,a,q[0],q[1]))
  const=update_consts(m,o,const)
 branch_states=set();branch_sites=set();carried=set();calls=[];icalls=[];ijumps=[];hits=[];ends=Counter()
 for li,la,lr,ea in loads:
  q=[(li+1,{lr:False})];seen=set()
  while q:
   idx,regs=q.pop()
   if idx<0 or idx>=len(rows):ends['out']+=1;continue
   key=(idx,tuple(sorted(regs.items())))
   if key in seen:continue
   seen.add(key);a,m,o=rows[idx]
   if m in {'call','jmp'}:
    if o in regs:hits.append((la,ea,a,m,o,tuple(sorted(regs))));continue
    t=imm(o)
    if m=='jmp' and t is not None and t in by:
     carried.add(la);branch_states.add((la,a,t,tuple(sorted(regs.items()))));branch_sites.add(a);q.append((by[t],dict(regs)));continue
    if m=='call' and t is not None:calls.append((la,ea,a,t,tuple(sorted(regs))))
    elif m=='call':icalls.append((la,ea,a,o,tuple(sorted(regs))))
    else:ijumps.append((la,ea,a,o,tuple(sorted(regs))))
    continue
   if (m.startswith('j') and m!='jmp') or m.startswith('loop'):
    t=imm(o);carried.add(la);branch_states.add((la,a,t,tuple(sorted(regs.items()))));branch_sites.add(a)
    if t is not None and t in by:q.append((by[t],dict(regs)))
    if idx+1<len(rows):q.append((idx+1,dict(regs)))
    continue
   if m in {'ret','retn','int','int3','ud2','iret','iretd'}:ends['terminal']+=1;continue
   nr=apply_taint(m,o,regs)
   if not nr:ends['taint_dead']+=1;continue
   q.append((idx+1,nr))
 return {'decoded_instruction_count':len(rows),'base_indexed_data_load_count':len(loads),'unique_effective_address_count':len({x[3] for x in loads}),'direct_cfg_carried_load_count':len(carried),'direct_cfg_carried_load_sites':[f'0x{x:08x}' for x in sorted(carried)],'direct_branch_state_event_count':len(branch_states),'direct_branch_site_count':len(branch_sites),'tainted_register_indirect_transfer_count':len(hits),'tainted_register_indirect_transfers':[{'load_site':f'0x{x[0]:08x}','effective_address':f'0x{x[1]:08x}','transfer_site':f'0x{x[2]:08x}','kind':x[3],'transfer_register':x[4],'live_taint_registers':list(x[5])} for x in hits],'direct_call_boundary_count':len(calls),'direct_call_boundary_unique_load_call_pair_count':len({(x[0],x[2]) for x in calls}),'direct_call_boundary_unique_site_count':len({x[2] for x in calls}),'indirect_call_boundary_count':len(icalls),'indirect_call_boundaries':[{'load_site':f'0x{x[0]:08x}','effective_address':f'0x{x[1]:08x}','call_site':f'0x{x[2]:08x}','call_register':x[3],'live_taint_registers':list(x[4])} for x in icalls],'indirect_jump_boundary_count':len(ijumps),'indirect_jump_boundaries':[{'load_site':f'0x{x[0]:08x}','effective_address':f'0x{x[1]:08x}','jump_site':f'0x{x[2]:08x}','jump_register':x[3],'live_taint_registers':list(x[4])} for x in ijumps],'taint_dead_terminal_state_count':ends['taint_dead'],'terminal_return_or_trap_state_count':ends['terminal'],'fixed_point_maxout_count':0}
def analyze(exe):
 if hashlib.sha256(exe.read_bytes()).hexdigest()!=SHA:raise ValueError('unexpected executable SHA')
 r=scan(dis(exe));expected=(2847850,63,51,44,228,199,2,56,54,54,9,0,107,6)
 actual=(r['decoded_instruction_count'],r['base_indexed_data_load_count'],r['unique_effective_address_count'],r['direct_cfg_carried_load_count'],r['direct_branch_state_event_count'],r['direct_branch_site_count'],r['tainted_register_indirect_transfer_count'],r['direct_call_boundary_count'],r['direct_call_boundary_unique_load_call_pair_count'],r['direct_call_boundary_unique_site_count'],r['indirect_call_boundary_count'],r['indirect_jump_boundary_count'],r['taint_dead_terminal_state_count'],r['terminal_return_or_trap_state_count'])
 if actual!=expected:raise AssertionError((actual,r))
 return r
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
