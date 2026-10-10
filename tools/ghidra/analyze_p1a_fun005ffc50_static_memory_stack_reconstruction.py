#!/usr/bin/env python3
"""Bound image-backed and explicit stack-local reconstruction of FUN_005ffc50."""
from __future__ import annotations
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun005ffc50StaticMemoryStackReconstruction/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50SimpleImmediateReconstruction/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET=0x005FFC50
MASK=0xffffffff
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB_TO_32={
 'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx',
 'dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp','sp':'esp'
}
# Only executable/read-only image bytes are treated as stable static dword seeds.
SECTIONS={
 '.text':(0x00401000,0x00401000+0x006a4489,0x00000400),
 '.rdata':(0x00aa6000,0x00aa6000+0x000dabb7,0x006a4a00),
}
INST_RE=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
IMM_RE=re.compile(r'^(?:0x([0-9a-fA-F]+)|(-?\d+))$')
STACK_RE=re.compile(r'^(?:BYTE PTR |WORD PTR |DWORD PTR |QWORD PTR )?\[(ebp|esp)([+-]0x[0-9a-fA-F]+)?\]$')
ABS_MEM_RE=re.compile(r'^(?:BYTE PTR |WORD PTR |DWORD PTR |QWORD PTR )?(?:ds:)?0x([0-9a-fA-F]+)$')
MEM_RE=re.compile(r'^(?:BYTE PTR |WORD PTR |DWORD PTR |QWORD PTR )?\[(.+)\]$')
WRITE_FIRST={'mov','lea','add','sub','xor','or','and','shl','sal','shr','sar','inc','dec','imul','neg','not','movzx','movsx','pop'}
BOUNDARY={'ret','retn','iret','iretd','int','int3','ud2','leave'}

def norm(s:str)->str:return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def imm(s:str):
 m=IMM_RE.match(s.strip())
 if not m:return None
 return (int(m.group(1),16) if m.group(1) is not None else int(m.group(2)))&MASK

def signed_disp(s:str|None)->int:
 if not s:return 0
 return int(s[1:],16) if s[0]=='+' else -int(s[1:],16)

def section_dword(blob:bytes,va:int):
 for name,(start,end,raw) in SECTIONS.items():
  if start<=va<=end-4:
   return struct.unpack_from('<I',blob,raw+va-start)[0],name
 return None

def eval_address_expr(expr:str,consts:dict[str,int]):
 """Evaluate a narrow Intel address expression containing known GPR terms and immediates."""
 x=expr.replace('-','+-')
 total=0;used=False
 for term in x.split('+'):
  term=term.strip()
  if not term:continue
  sign=1
  if term.startswith('-'):
   sign=-1;term=term[1:]
  if '*' in term:
   r,sc=term.split('*',1)
   if r not in REGS or r not in consts or sc not in {'1','2','4','8'}:return None
   total+=sign*consts[r]*int(sc);used=True;continue
  if term in REGS:
   if term not in consts:return None
   total+=sign*consts[term];used=True;continue
  v=imm(term)
  if v is None:return None
  # imm() wraps negatives; address syntax here already split the sign.
  total+=sign*v;used=True
 return total&MASK if used else None

def first_dest_base(mn:str,ops:str):
 if mn not in WRITE_FIRST:return None
 d=ops.split(',',1)[0].strip()
 if d in REGS:return d
 return SUB_TO_32.get(d)

def scan_lines(lines,blob:bytes):
 consts:dict[str,int]={};stack:dict[int,int]={};esp_delta=0;ebp_delta=None
 n=0;static_loads=[];reg_mats=[];stack_mats=[];transfers=[]
 def clear_region():
  nonlocal esp_delta,ebp_delta
  consts.clear();stack.clear();esp_delta=0;ebp_delta=None
 def stack_key(op:str):
  m=STACK_RE.match(op)
  if not m:return None
  base,disp=m.groups();d=signed_disp(disp)
  if base=='esp':return esp_delta+d
  if ebp_delta is None:return None
  return ebp_delta+d
 def static_value(op:str):
  m=ABS_MEM_RE.match(op)
  if m:
   va=int(m.group(1),16);r=section_dword(blob,va)
   return (r[0],('absolute',va,r[1])) if r else (None,None)
  m=MEM_RE.match(op)
  if not m:return None,None
  va=eval_address_expr(m.group(1),consts)
  if va is None:return None,None
  r=section_dword(blob,va)
  return (r[0],('computed',va,r[1])) if r else (None,None)
 def read_value(op:str):
  v=imm(op)
  if v is not None:return v,('immediate',op)
  if op in REGS:return consts.get(op),('register',op)
  k=stack_key(op)
  if k is not None:return stack.get(k),('stack',k)
  return static_value(op)
 def record_materializations(addr:int,mn:str,ops:str,before_regs:set[str],before_stack:set[int]):
  for r,v in sorted(consts.items()):
   if v==TARGET and r not in before_regs:
    reg_mats.append({'site':f'0x{addr:08x}','register':r,'instruction':f'{mn} {ops}'.rstrip()})
  for k,v in sorted(stack.items()):
   if v==TARGET and k not in before_stack:
    stack_mats.append({'site':f'0x{addr:08x}','stack_offset_from_region_entry':k,'instruction':f'{mn} {ops}'.rstrip()})
 for line in lines:
  m=INST_RE.match(line)
  if not m:continue
  n+=1;addr=int(m.group(1),16);mn=m.group(2).lower();ops=norm(m.group(3));parts=[x.strip() for x in ops.split(',')] if ops else []
  before_regs={r for r,v in consts.items() if v==TARGET};before_stack={k for k,v in stack.items() if v==TARGET}
  # Resolve only indirect register/stack/static-memory transfers; direct calls are upstream territory.
  if mn in {'call','jmp'}:
   kind=None;src=None
   if ops in REGS and consts.get(ops)==TARGET:kind='register';src=ops
   else:
    k=stack_key(ops)
    if k is not None and stack.get(k)==TARGET:kind='stack';src=k
    else:
     v,prov=static_value(ops)
     if v==TARGET:kind='static_memory';src=prov
   if kind:
    transfers.append({'site':f'0x{addr:08x}','kind':mn,'source_kind':kind,'source':src})
   clear_region();continue
  if mn.startswith('j') or mn.startswith('loop') or mn in BOUNDARY:
   clear_region();continue
  if mn=='push' and len(parts)==1:
   v,_=read_value(parts[0]);esp_delta-=4
   if v is None:stack.pop(esp_delta,None)
   else:stack[esp_delta]=v
  elif mn=='pop' and len(parts)==1:
   d=parts[0];v=stack.get(esp_delta);stack.pop(esp_delta,None)
   if d in REGS:
    if v is None:consts.pop(d,None)
    else:consts[d]=v
    if d=='ebp':ebp_delta=None
   esp_delta+=4
  elif mn=='mov' and len(parts)==2:
   d,s=parts
   if d=='ebp' and s=='esp':
    consts.pop('ebp',None);ebp_delta=esp_delta
   elif d=='esp' and s=='ebp':
    if ebp_delta is None:clear_region()
    else:esp_delta=ebp_delta
   elif d in REGS:
    v,prov=read_value(s)
    if v is None:consts.pop(d,None)
    else:
     consts[d]=v
     if prov and prov[0] in {'absolute','computed'}:
      static_loads.append({'site':f'0x{addr:08x}','register':d,'value':f'0x{v:08x}','address':f'0x{prov[1]:08x}','section':prov[2]})
   else:
    k=stack_key(d)
    if k is not None:
     v,_=read_value(s)
     if v is None:stack.pop(k,None)
     else:stack[k]=v
    elif '[' in d:
     # Unknown memory write could alias a tracked stack slot through a pointer.
     stack.clear()
  elif mn=='lea' and len(parts)==2 and parts[0] in REGS:
   d,s=parts;m2=MEM_RE.match(s);v=eval_address_expr(m2.group(1),consts) if m2 else None
   if v is None:consts.pop(d,None)
   else:consts[d]=v
  elif mn in {'add','sub'} and len(parts)==2 and parts[0]=='esp':
   k=imm(parts[1])
   if k is None:clear_region()
   else:esp_delta += k if mn=='add' else -k
  elif mn in {'add','sub','xor','or','and'} and len(parts)==2:
   d,s=parts;sv,_=read_value(s)
   if d in REGS:
    old=consts.get(d)
    if s==d and mn in {'xor','sub'}:consts[d]=0
    elif old is None or sv is None:consts.pop(d,None)
    else:
     consts[d]=({'add':old+sv,'sub':old-sv,'xor':old^sv,'or':old|sv,'and':old&sv}[mn])&MASK
   else:
    k=stack_key(d)
    if k is not None:
     old=stack.get(k)
     if old is None or sv is None:stack.pop(k,None)
     else:stack[k]=({'add':old+sv,'sub':old-sv,'xor':old^sv,'or':old|sv,'and':old&sv}[mn])&MASK
    elif '[' in d:stack.clear()
  elif mn in {'shl','sal','shr','sar'} and len(parts)==2:
   d,s=parts;k=imm(s)
   def shifted(v):
    if v is None or k is None:return None
    kk=k&31
    if mn in {'shl','sal'}:return (v<<kk)&MASK
    if mn=='shr':return (v>>kk)&MASK
    signed=v if v<0x80000000 else v-0x100000000
    return (signed>>kk)&MASK
   if d in REGS:
    v=shifted(consts.get(d));consts.pop(d,None) if v is None else consts.__setitem__(d,v)
   else:
    q=stack_key(d)
    if q is not None:
     v=shifted(stack.get(q));stack.pop(q,None) if v is None else stack.__setitem__(q,v)
    elif '[' in d:stack.clear()
  elif mn in {'inc','dec','neg','not'} and len(parts)==1:
   d=parts[0]
   def unary(v):
    if v is None:return None
    return ({'inc':v+1,'dec':v-1,'neg':-v,'not':~v}[mn])&MASK
   if d in REGS:
    v=unary(consts.get(d));consts.pop(d,None) if v is None else consts.__setitem__(d,v)
   else:
    q=stack_key(d)
    if q is not None:
     v=unary(stack.get(q));stack.pop(q,None) if v is None else stack.__setitem__(q,v)
    elif '[' in d:stack.clear()
  elif mn=='imul' and len(parts)==3 and parts[0] in REGS:
   d,s,k=parts;v,_=read_value(s);kk=imm(k)
   if v is None or kk is None:consts.pop(d,None)
   else:consts[d]=(v*kk)&MASK
  elif mn=='xchg' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
   a,b=parts;av=consts.get(a);bv=consts.get(b)
   consts.pop(a,None) if bv is None else consts.__setitem__(a,bv)
   consts.pop(b,None) if av is None else consts.__setitem__(b,av)
  else:
   d=first_dest_base(mn,ops)
   if d:consts.pop(d,None)
   if parts and '[' in parts[0] and stack_key(parts[0]) is None:stack.clear()
   if mn in {'mul','div','idiv','cdq','cwd','cwde'}:
    consts.pop('eax',None);consts.pop('edx',None)
  record_materializations(addr,mn,ops,before_regs,before_stack)
 return n,static_loads,reg_mats,stack_mats,transfers

def disassemble(exe:Path,blob:bytes):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace')
 assert p.stdout
 result=scan_lines(p.stdout,blob);err=p.stderr.read() if p.stderr else '';rc=p.wait()
 if rc:raise RuntimeError(err)
 return result

def analyze(exe:Path,upstream:Path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 a=up.get('adjudication',{})
 if not a.get('p13a_fun005ffc50_simple_straight_line_immediate_reconstruction_subset_complete'):raise AssertionError('upstream simple reconstruction incomplete')
 if a.get('simple_straight_line_fun005ffc50_reconstruction_found') or a.get('simple_straight_line_fun005ffc50_indirect_transfer_found'):
  raise AssertionError('upstream simple reconstruction unexpectedly positive')
 n,loads,rm,sm,xf=disassemble(exe,blob)
 if rm or sm or xf:raise AssertionError(('static/stack reconstruction unexpectedly positive',rm,sm,xf))
 section_counts={s:sum(1 for x in loads if x['section']==s) for s in SECTIONS}
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM,
               'static_seed_sections':{k:{'start':f'0x{v[0]:08x}','end_exclusive':f'0x{v[1]:08x}','raw_offset':f'0x{v[2]:08x}'} for k,v in SECTIONS.items()}},
  'scope':{
   'target':'FUN_005ffc50','target_address':'0x005ffc50','decoded_instruction_count':n,
   'tracked_static_sources':['32-bit dword loads from image .text','.rdata'],
   'tracked_stack_sources':['explicit [esp+disp] slots with ESP delta','explicit [ebp+disp] slots after mov ebp,esp','push/pop values'],
   'tracked_transformations':['mov','lea over known GPR address terms','add/sub/xor/or/and','shifts','inc/dec/neg/not','imul reg,known,imm','xchg'],
   'state_resets_on':['call/jmp after transfer check','conditional branch/loop','ret/int/ud2/leave'],
   'unknown_pointer_memory_write_clears_stack_constants':True,
  },
  'inventory':{
   'image_backed_dword_load_count':len(loads),'image_backed_dword_load_count_by_section':section_counts,
   'exact_target_register_materialization_count':len(rm),'exact_target_stack_materialization_count':len(sm),
   'exact_target_indirect_transfer_count':len(xf),'register_materializations':rm,'stack_materializations':sm,'indirect_transfers':xf,
  },
  'adjudication':{
   'p13a_fun005ffc50_readonly_image_and_explicit_stack_reconstruction_subset_complete':True,
   'readonly_image_backed_fun005ffc50_reconstruction_found':False,
   'explicit_stack_local_fun005ffc50_reconstruction_found':False,
   'readonly_image_or_stack_fun005ffc50_indirect_transfer_found':False,
   'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
   'encoded_or_reconstructed_callback_entry_ruled_out':False,
   'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,
   'fun0067b660_callback_argument_provenance_complete':False,
   'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
   'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
   'This contract tracks only image-backed 32-bit dword seeds from .text/.rdata and explicit syntactic stack locals within one straight-line region.',
   'Writable .data state is deliberately not treated as immutable because startup/runtime code may replace it before a load.',
   'Unknown pointer-based memory writes clear tracked stack constants; memory aliasing through arbitrary pointers is not proven absent.',
   'Calls and control-flow transfers reset state, so return-address/PIC reconstruction, inter-block dataflow, return-value provenance, runtime-generated pointers, encoded/split values, and writable-memory callback slots remain open.',
   'No global reconstructed-entry, callback, slot0, slot1, stored-alias, runtime selected-wheel-store-negative, or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Trace writable-memory/runtime callback slots, return-address/PIC construction, or inter-block incoming entry to FUN_005ffc50; direct/raw, simple GPR, read-only image seed and explicit stack-local reconstruction subsets are now separately bounded.'
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
