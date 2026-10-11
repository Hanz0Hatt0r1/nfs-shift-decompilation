#!/usr/bin/env python3
"""Bound trivial direct-callee constant-return provenance into FUN_005ffc50 reconstruction."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from collections import Counter
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50TrivialConstantReturnProducers/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50FourEdgeConstantCarry/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET=0x005ffc50;MASK=0xffffffff;MAX_CALLEE_INSNS=64
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp'}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
IMM=re.compile(r'^(?:0x([0-9a-fA-F]+)|(-?\d+))$')
MEM_SIMPLE=re.compile(r'^\[(eax|ebx|ecx|edx|esi|edi|ebp)([+-]0x[0-9a-fA-F]+)?\]$')
MEM_SCALE=re.compile(r'^\[(eax|ebx|ecx|edx|esi|edi|ebp)\*([1248])([+-]0x[0-9a-fA-F]+)?\]$')
WRITE={'mov','lea','add','sub','xor','or','and','shl','sal','shr','sar','inc','dec','imul','neg','not','movzx','movsx','pop'}
STOP={'ret','retn','iret','iretd','int','int3','ud2'}
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def imm(s):
 m=IMM.match(s.strip())
 if not m:return None
 return (int(m.group(1),16) if m.group(1) is not None else int(m.group(2)))&MASK
def memexpr(s,c):
 m=MEM_SIMPLE.match(s)
 if m:
  r,d=m.groups()
  if r not in c:return None
  dd=int(d,16) if d and d[0]=='+' else (-int(d[1:],16) if d else 0);return(c[r]+dd)&MASK
 m=MEM_SCALE.match(s)
 if m:
  r,sc,d=m.groups()
  if r not in c:return None
  dd=int(d,16) if d and d[0]=='+' else (-int(d[1:],16) if d else 0);return(c[r]*int(sc)+dd)&MASK
 return None
def dest(mn,op):
 if mn not in WRITE:return None
 d=op.split(',',1)[0].strip();return d if d in REGS else SUB.get(d)
def apply(mn,op,c):
 p=[x.strip() for x in op.split(',')] if op else []
 if mn=='xchg' and len(p)==2 and p[0] in REGS and p[1] in REGS:
  a,b=p;av=c.get(a);bv=c.get(b)
  if bv is None:c.pop(a,None)
  else:c[a]=bv
  if av is None:c.pop(b,None)
  else:c[b]=av
  return
 if mn=='mov' and len(p)==2 and p[0] in REGS:
  d,s=p;v=imm(s);v=c.get(s) if v is None and s in REGS else v
  if v is None:c.pop(d,None)
  else:c[d]=v
  return
 if mn=='lea' and len(p)==2 and p[0] in REGS:
  d,s=p;v=memexpr(s,c)
  if v is None:c.pop(d,None)
  else:c[d]=v
  return
 if mn in {'add','sub','xor','or','and'} and len(p)==2 and p[0] in REGS:
  d,s=p;old=c.get(d);k=imm(s);k=c.get(s) if k is None and s in REGS else k
  if s==d and mn in {'xor','sub'}:c[d]=0;return
  if old is None or k is None:c.pop(d,None);return
  c[d]=({'add':old+k,'sub':old-k,'xor':old^k,'or':old|k,'and':old&k}[mn])&MASK;return
 if mn in {'shl','sal','shr','sar'} and len(p)==2 and p[0] in REGS:
  d,s=p;v=c.get(d);k=imm(s)
  if v is None or k is None:c.pop(d,None);return
  k&=31
  if mn in {'shl','sal'}:v=(v<<k)&MASK
  elif mn=='shr':v>>=k
  else:v=((v if v<0x80000000 else v-0x100000000)>>k)&MASK
  c[d]=v;return
 if mn in {'inc','dec','neg','not'} and len(p)==1 and p[0] in REGS:
  d=p[0];v=c.get(d)
  if v is None:c.pop(d,None);return
  c[d]=({'inc':v+1,'dec':v-1,'neg':-v,'not':~v}[mn])&MASK;return
 if mn=='imul' and len(p)==3 and p[0] in REGS and p[1] in REGS:
  d,s,k=p;v=c.get(s);kk=imm(k)
  if v is None or kk is None:c.pop(d,None)
  else:c[d]=(v*kk)&MASK
  return
 d=dest(mn,op)
 if d:c.pop(d,None)
 if mn in {'mul','div','idiv','cdq','cwd','cwde'}:c.pop('eax',None);c.pop('edx',None)
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True);out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def dt(op):
 try:return int(op,16)
 except:return None
def classify_trivial_returners(rows):
 idx={a:i for i,(a,_,_) in enumerate(rows)}
 targets=sorted({t for _,m,o in rows if m=='call' and (t:=dt(o)) is not None and t in idx})
 ret={};step_hist=Counter()
 for t in targets:
  c={};j=idx[t];steps=0
  while j<len(rows) and steps<MAX_CALLEE_INSNS:
   a,mn,op=rows[j];steps+=1
   if mn.startswith('ret'):
    if 'eax' in c:ret[t]={'value':c['eax'],'steps':steps,'ret_site':a}
    break
   if mn=='call' or mn=='jmp' or mn.startswith('j') or mn.startswith('loop') or mn in {'iret','iretd','int','int3','ud2'}:break
   apply(mn,op,c);j+=1
  if t in ret:step_hist[ret[t]['steps']]+=1
 return idx,targets,ret,dict(sorted(step_hist.items()))
def scan(rows):
 idx,targets,ret,step_hist=classify_trivial_returners(rows)
 callsites=[];mats=[];xf=[];post_sim=0;value_hist=Counter()
 for i,(a,mn,op) in enumerate(rows):
  if mn!='call':continue
  t=dt(op)
  if t not in ret:continue
  info=ret[t];value_hist[info['value']]+=1
  callsites.append({'site':f'0x{a:08x}','callee':f'0x{t:08x}','return_value':f'0x{info["value"]:08x}'})
  c={'eax':info['value']};j=i+1
  while j<len(rows):
   aa,mm,oo=rows[j];post_sim+=1
   if mm in {'call','jmp'}:
    if oo in REGS and c.get(oo)==TARGET:xf.append({'producer_call':f'0x{a:08x}','callee':f'0x{t:08x}','site':f'0x{aa:08x}','kind':mm,'register':oo})
    break
   if mm.startswith('j') or mm.startswith('loop') or mm in STOP:break
   before={r for r,v in c.items() if v==TARGET};apply(mm,oo,c)
   for r,v in c.items():
    if v==TARGET and r not in before:mats.append({'producer_call':f'0x{a:08x}','callee':f'0x{t:08x}','site':f'0x{aa:08x}','register':r,'instruction':f'{mm} {oo}'.rstrip()})
   j+=1
 return {'direct_call_target_count':len(targets),'trivial_constant_return_producer_count':len(ret),'trivial_constant_return_callsite_count':len(callsites),'unique_return_constant_count':len(value_hist),'producer_entry_step_histogram':{str(k):v for k,v in step_hist.items()},'post_call_simulated_instruction_count':post_sim,'materializations':mats,'indirect_transfers':xf}
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up.get('adjudication',{}).get('p13a_fun005ffc50_up_to_four_direct_cfg_edge_constant_carry_subset_complete'):raise AssertionError('upstream four-edge subset incomplete')
 rows=dis(exe);r=scan(rows)
 if r['materializations'] or r['indirect_transfers']:raise AssertionError(('trivial return producer positive',r))
 if len(rows)!=2847850 or r['direct_call_target_count']!=25666 or r['trivial_constant_return_producer_count']!=280 or r['trivial_constant_return_callsite_count']!=859:raise AssertionError(('inventory drift',len(rows),r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'target':'FUN_005ffc50','target_address':'0x005ffc50','decoded_instruction_count':len(rows),'producer_class':'direct-call targets whose entry basic block reaches ret within 64 instructions before any call/branch and has exact EAX','post_call_class':'seed exact producer EAX return and scan caller straight-line suffix until next control transfer'},'inventory':r,'adjudication':{'p13a_fun005ffc50_trivial_constant_return_producer_subset_complete':True,'trivial_return_fun005ffc50_materialization_found':False,'trivial_return_fun005ffc50_indirect_transfer_found':False,'return_value_fun005ffc50_provenance_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,'encoded_or_reconstructed_callback_entry_ruled_out':False,'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'fun0067b660_callback_argument_provenance_complete':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['Only direct callees whose entry basic block itself reaches ret before any call or branch are classified; branched callees and memory-derived return values remain open.','Only the immediate straight-line caller suffix after the direct call is scanned; post-call CFG carry is not composed here.','This is a narrow return-value subset, not global return-value provenance closure.','No global reconstructed-entry, callback, writable-runtime, stored-alias, slot0, slot1 or aggregate P1.3 gate is promoted.'],'next_step':'Extend return-value provenance to branched/memory-derived producers or writable/runtime memory; trivial direct constant-return producers no longer need to be rescanned.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
