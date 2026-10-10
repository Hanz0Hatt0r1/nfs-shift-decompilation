#!/usr/bin/env python3
"""Bound simple straight-line GPR reconstruction of FUN_005ffc50 in retail SHIFT.exe."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50SimpleImmediateReconstruction/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50DirectCregEntryClosure/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET=0x005FFC50
MASK=0xffffffff
REGS={'eax','ebx','ecx','edx','esi','edi','ebp'}
SUB_TO_32={'ax':'eax','al':'eax','ah':'eax','bx':'ebx','bl':'ebx','bh':'ebx','cx':'ecx','cl':'ecx','ch':'ecx','dx':'edx','dl':'edx','dh':'edx','si':'esi','di':'edi','bp':'ebp','sp':'esp'}
INST_RE=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
IMM_RE=re.compile(r'^(?:0x([0-9a-fA-F]+)|(-?\d+))$')
MEM_SIMPLE_RE=re.compile(r'^\[(eax|ebx|ecx|edx|esi|edi|ebp)([+-]0x[0-9a-fA-F]+)?\]$')
MEM_SCALE_RE=re.compile(r'^\[(eax|ebx|ecx|edx|esi|edi|ebp)\*([1248])([+-]0x[0-9a-fA-F]+)?\]$')
WRITE_FIRST={'mov','lea','add','sub','xor','or','and','shl','sal','shr','sar','inc','dec','imul','neg','not','movzx','movsx','pop'}
BOUNDARY={'ret','retn','iret','iretd','int','int3','ud2'}
def norm(s:str)->str:return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def imm(s:str):
 m=IMM_RE.match(s.strip())
 if not m:return None
 if m.group(1) is not None:return int(m.group(1),16)&MASK
 return int(m.group(2))&MASK
def parse_mem_expr(s:str,consts:dict[str,int]):
 x=s.strip()
 if x.startswith('DWORD PTR '):x=x[len('DWORD PTR '):]
 m=MEM_SIMPLE_RE.match(x)
 if m:
  r,disp=m.groups()
  if r not in consts:return None
  d=int(disp,16) if disp and disp.startswith('+') else (-int(disp[1:],16) if disp and disp.startswith('-') else 0)
  return (consts[r]+d)&MASK
 m=MEM_SCALE_RE.match(x)
 if m:
  r,scale,disp=m.groups()
  if r not in consts:return None
  d=int(disp,16) if disp and disp.startswith('+') else (-int(disp[1:],16) if disp and disp.startswith('-') else 0)
  return (consts[r]*int(scale)+d)&MASK
 return None
def first_dest_base(mn:str,ops:str):
 if mn not in WRITE_FIRST:return None
 d=ops.split(',',1)[0].strip()
 if d in REGS:return d
 return SUB_TO_32.get(d)
def apply_instruction(mn:str,ops:str,consts:dict[str,int]):
 parts=[x.strip() for x in ops.split(',')] if ops else []
 if mn=='xchg' and len(parts)==2 and parts[0] in REGS and parts[1] in REGS:
  a,b=parts;av=consts.get(a);bv=consts.get(b)
  if bv is None:consts.pop(a,None)
  else:consts[a]=bv
  if av is None:consts.pop(b,None)
  else:consts[b]=av
  return
 if mn=='mov' and len(parts)==2 and parts[0] in REGS:
  d,s=parts;v=imm(s)
  if v is None:v=consts.get(s) if s in REGS else None
  if v is None:consts.pop(d,None)
  else:consts[d]=v
  return
 if mn=='lea' and len(parts)==2 and parts[0] in REGS:
  d,s=parts;v=parse_mem_expr(s,consts)
  if v is None:consts.pop(d,None)
  else:consts[d]=v
  return
 if mn in {'add','sub','xor','or','and'} and len(parts)==2 and parts[0] in REGS:
  d,s=parts;v=consts.get(d);k=imm(s)
  if k is None and s in REGS:k=consts.get(s)
  if s==d and mn in {'xor','sub'}:consts[d]=0;return
  if v is None or k is None:consts.pop(d,None);return
  if mn=='add':v=(v+k)&MASK
  elif mn=='sub':v=(v-k)&MASK
  elif mn=='xor':v=(v^k)&MASK
  elif mn=='or':v=(v|k)&MASK
  else:v=(v&k)&MASK
  consts[d]=v;return
 if mn in {'shl','sal','shr','sar'} and len(parts)==2 and parts[0] in REGS:
  d,s=parts;v=consts.get(d);k=imm(s)
  if v is None or k is None:consts.pop(d,None);return
  k&=31
  if mn in {'shl','sal'}:v=(v<<k)&MASK
  elif mn=='shr':v=(v>>k)&MASK
  else:
   signed=v if v<0x80000000 else v-0x100000000;v=(signed>>k)&MASK
  consts[d]=v;return
 if mn in {'inc','dec','neg','not'} and len(parts)==1 and parts[0] in REGS:
  d=parts[0];v=consts.get(d)
  if v is None:consts.pop(d,None);return
  if mn=='inc':v=(v+1)&MASK
  elif mn=='dec':v=(v-1)&MASK
  elif mn=='neg':v=(-v)&MASK
  else:v=(~v)&MASK
  consts[d]=v;return
 if mn=='imul' and len(parts)==3 and parts[0] in REGS and parts[1] in REGS:
  d,s,k=parts;v=consts.get(s);kk=imm(k)
  if v is None or kk is None:consts.pop(d,None)
  else:consts[d]=(v*kk)&MASK
  return
 d=first_dest_base(mn,ops)
 if d:consts.pop(d,None)
 if mn in {'mul','div','idiv'}:consts.pop('eax',None);consts.pop('edx',None)
 if mn in {'cdq','cwd','cwde'}:consts.pop('eax',None);consts.pop('edx',None)
def scan_lines(lines):
 consts={};instruction_count=0;materializations=[];indirect_transfers=[]
 for line in lines:
  m=INST_RE.match(line)
  if not m:continue
  instruction_count+=1;addr=int(m.group(1),16);mn=m.group(2).lower();ops=norm(m.group(3))
  if mn in {'call','jmp'}:
   if ops in REGS and consts.get(ops)==TARGET:indirect_transfers.append({'site':f'0x{addr:08x}','kind':mn,'register':ops})
   consts.clear();continue
  if mn.startswith('j') or mn in BOUNDARY or mn.startswith('loop'):consts.clear();continue
  before={r for r,v in consts.items() if v==TARGET};apply_instruction(mn,ops,consts)
  for r,v in sorted(consts.items()):
   if v==TARGET and r not in before:materializations.append({'site':f'0x{addr:08x}','register':r,'instruction':f'{mn} {ops}'.rstrip()})
 return instruction_count,materializations,indirect_transfers
def disassemble(exe:Path):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout
 result=scan_lines(p.stdout);err=p.stderr.read() if p.stderr else '';rc=p.wait()
 if rc:raise RuntimeError(err)
 return result
def analyze(exe:Path,upstream:Path):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 a=up.get('adjudication',{})
 if not a.get('p13a_fun005ffc50_direct_creg_entry_subset_complete'):raise AssertionError('upstream direct subset incomplete')
 if up['static_pointer_literal_surface']['exact_absolute_va_occurrence_count'] or up['static_pointer_literal_surface']['exact_rva_occurrence_count']:raise AssertionError('raw static pointer unexpectedly positive upstream')
 n,mats,transfers=disassemble(exe)
 if mats or transfers:raise AssertionError(('simple reconstruction unexpectedly positive',mats,transfers))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'target':'FUN_005ffc50','target_address':'0x005ffc50','decoded_instruction_count':n,'straight_line_region_resets_on':['call','jmp','conditional branch','loop','ret/int/ud2'],'modeled_constant_operations':['mov reg,imm/reg','lea reg,[known_reg(+/-imm)]','lea reg,[known_reg*scale(+/-imm)]','add/sub/xor/or/and reg,imm/known_reg','shl/sal/shr/sar reg,imm','inc/dec/neg/not reg','imul reg,known_reg,imm','xchg reg,reg'],'subregister_or_unmodeled_register_writes_kill_constant':True},'inventory':{'exact_target_materialization_count':len(mats),'exact_target_indirect_call_or_jump_count':len(transfers),'materializations':mats,'indirect_transfers':transfers},'adjudication':{'p13a_fun005ffc50_simple_straight_line_immediate_reconstruction_subset_complete':True,'simple_straight_line_fun005ffc50_reconstruction_found':False,'simple_straight_line_fun005ffc50_indirect_transfer_found':False,'encoded_or_reconstructed_callback_entry_ruled_out':False,'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'fun0067b660_callback_argument_provenance_complete':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This is a path-insensitive straight-line constant-propagation subset only. State is deliberately discarded at every control-flow transfer or call.','It does not model constants loaded from memory, stack spill/reload, split-byte/word assembly, table lookup, relocation, return values, or runtime-generated pointers.','The merged direct/raw-literal closure remains authoritative for direct calls and exact raw VA/RVA literals; this contract adds only multi-instruction GPR reconstruction.','No global reconstructed-entry, callback, slot0, slot1, stored-alias, or aggregate P1.3 gate is promoted.'],'next_step':'Trace memory-backed, stack-backed, or runtime/indirect entry to FUN_005ffc50; direct/raw and simple straight-line immediate reconstruction subsets are now separately bounded.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
