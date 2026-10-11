#!/usr/bin/env python3
"""Bound base/index-addressed writable .data loads and same-register near transfers."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from collections import Counter
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50BaseIndexedDataNearTransfer/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50AbsoluteDataEspNormalization/1'
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
def norm(s): return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe:Path):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace'); assert p.stdout
 for line in p.stdout:
  m=I.match(line)
  if m: yield int(m.group(1),16),m.group(2).lower(),norm(m.group(3))
 err=p.stderr.read() if p.stderr else ''
 if p.wait(): raise RuntimeError(err)
def parse_imm(s):
 m=IMM.fullmatch(s)
 if not m:return None
 return int(m.group(1),16) if m.group(1) else int(m.group(2),10)
def split_terms(expr):
 return re.findall(r'[+-]?[^+-]+',expr.replace(' ',''))
def eval_expr(expr,consts):
 total=0; used_reg=False
 for raw in split_terms(expr):
  sign=-1 if raw.startswith('-') else 1
  t=raw[1:] if raw[:1] in '+-' else raw
  if '*' in t:
   r,sc=t.split('*',1)
   if r not in REGS or r not in consts:return None
   scale=parse_imm(sc)
   if scale is None:return None
   total+=sign*consts[r]*scale;used_reg=True
  elif t in REGS:
   if t not in consts:return None
   total+=sign*consts[t];used_reg=True
  else:
   n=parse_imm(t)
   if n is None:return None
   total+=sign*n
 return (total & 0xffffffff) if used_reg else None
def parse_base_index_load(mn,ops,consts):
 if mn!='mov' or ',' not in ops:return None
 d,s=ops.split(',',1)
 if d not in REGS:return None
 q=MEM.fullmatch(s)
 if not q:return None
 ea=eval_expr(q.group(1),consts)
 if ea is not None and DATA_START<=ea<DATA_END:return d,ea,s
def writes_reg(mn,ops,reg):
 p=ops.split(',') if ops else []
 if mn=='xchg' and any(x==reg or SUB.get(x)==reg for x in p):return True
 if p and mn not in READ_ONLY_FIRST:
  d=p[0]
  if d==reg or SUB.get(d)==reg:return True
 if reg in {'eax','edx'} and mn in {'mul','div','idiv','cdq','cwd','cwde'}:return True
 if reg in {'eax','edx'} and mn=='imul' and len(p)==1:return True
 return False
def update_consts(mn,ops,consts):
 p=ops.split(',') if ops else []
 c=dict(consts)
 if mn=='mov' and len(p)==2 and p[0] in REGS:
  d,s=p
  n=parse_imm(s)
  if n is not None:c[d]=n&0xffffffff
  elif s in REGS and s in c:c[d]=c[s]
  else:c.pop(d,None)
 elif mn=='lea' and len(p)==2 and p[0] in REGS:
  d,s=p;q=MEM.fullmatch(s);v=eval_expr(q.group(1),c) if q else None
  if v is None:c.pop(d,None)
  else:c[d]=v
 elif mn in {'add','sub'} and len(p)==2 and p[0] in REGS:
  d,s=p;n=parse_imm(s)
  if d in c and n is not None:c[d]=(c[d]+(n if mn=='add' else -n))&0xffffffff
  else:c.pop(d,None)
 elif mn=='xor' and len(p)==2 and p[0] in REGS and p[0]==p[1]:c[p[0]]=0
 else:
  for r in REGS:
   if writes_reg(mn,ops,r):c.pop(r,None)
 return c
def scan_rows(rows):
 rows=list(rows);consts={};loads=[]
 for idx,(a,mn,ops) in enumerate(rows):
  q=parse_base_index_load(mn,ops,consts)
  if q:
   reg,ea,source=q;loads.append((idx,a,reg,ea,source))
  consts=update_consts(mn,ops,consts)
 hits=[];terms=Counter()
 for idx,a,reg,ea,source in loads:
  reason='window_exhausted'
  for j in range(idx+1,min(len(rows),idx+1+WINDOW)):
   b,mn,ops=rows[j]
   if mn in {'call','jmp'}:
    if ops==reg:
     hits.append({'load_site':f'0x{a:08x}','effective_address':f'0x{ea:08x}','source_operand':source,'transfer_site':f'0x{b:08x}','kind':mn,'transfer_register':reg,'distance':j-idx});reason='matched_transfer'
    else:reason='other_control_transfer'
    break
   if mn.startswith('j') or mn.startswith('loop') or mn in CONTROL_STOPS or mn in {'ret','retn'}:
    reason='other_control_transfer';break
   if writes_reg(mn,ops,reg):reason='register_clobber';break
  terms[reason]+=1
 return {'decoded_instruction_count':len(rows),'base_indexed_data_load_count':len(loads),'unique_effective_address_count':len({x[3] for x in loads}),'destination_register_counts':dict(sorted(Counter(x[2] for x in loads).items())),'same_register_indirect_transfer_count':len(hits),'same_register_indirect_transfers':hits,'termination_reason_counts':dict(sorted(terms.items()))}
def analyze(exe,upstream):
 sha=hashlib.sha256(exe.read_bytes()).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up['adjudication'].get('p13a_fun005ffc50_absolute_data_esp_normalization_subset_complete'):raise AssertionError('upstream incomplete')
 r=scan_rows(dis(exe))
 expected_regs={'eax':37,'ebx':4,'ecx':10,'edi':2,'edx':5,'esi':5}
 if (r['decoded_instruction_count'],r['base_indexed_data_load_count'],r['unique_effective_address_count'])!=(2847850,63,51):raise AssertionError(('inventory drift',r))
 if r['destination_register_counts']!=expected_regs:raise AssertionError(('register distribution drift',r))
 if r['same_register_indirect_transfer_count']!=0:raise AssertionError(('unexpected transfer',r))
 if r['termination_reason_counts']!={'other_control_transfer':58,'register_clobber':5}:raise AssertionError(('termination drift',r))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},'scope':{'data_start':f'0x{DATA_START:08x}','data_end_exclusive':f'0x{DATA_END:08x}','forward_window_decoded_instructions':WINDOW,'address_model':'straight-line exact GPR constants; effective address evaluated before MOV load','transfer_model':'same destination register only','unknown_base_or_index_policy':'exclude from this subset'},'inventory':r,'adjudication':{'p13a_fun005ffc50_base_indexed_data_same_register_near_transfer_subset_complete':True,'base_indexed_data_same_register_indirect_transfer_found':False,'register_copy_or_transform_after_base_indexed_load_ruled_out':False,'base_indexed_stack_spill_reload_ruled_out':False,'base_indexed_inter_block_carry_ruled_out':False,'base_indexed_writable_sources_ruled_out':False,'register_loaded_or_aliased_writable_slots_ruled_out':False,'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,'return_value_fun005ffc50_provenance_ruled_out':False,'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,'encoded_or_reconstructed_callback_entry_ruled_out':False,'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'fun0067b660_callback_argument_provenance_complete':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes only exact straight-line base/index effective-address MOV loads into writable .data and direct same-register CALL/JMP within 16 decoded instructions.','Register copies/transforms, spills/reloads, inter-block carry, aliases, heap/runtime values and global P1.3 gates remain open.'],'next_step':'Propagate these 63 base/index-addressed writable .data loads through GPR copies/transforms, stack carriers and bounded inter-block carry.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
