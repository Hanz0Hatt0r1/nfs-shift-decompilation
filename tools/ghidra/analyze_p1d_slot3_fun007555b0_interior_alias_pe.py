#!/usr/bin/env python3
"""Close the FUN_007555b0 wheel+0x80 interior-receiver alias against retail PE bytes."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3Fun007555b0InteriorAliasClosure/1"
PE_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"
START=0x007555B0
SIZE=364
MACHINE_SHA256="43aff676522a3b6b558980b56e29e289926893d266bf71e063b25d401d1e4881"
EXPECTED_MEMORY_OFFSETS=[0x1D0,0x1D8,0x1E0,0x1E8,0x1F0,0x1F8,0x200,0x208,0x210,0x218,0x220,0x228,0x230,0x238,0x240,0x248,0x250,0x258,0x260]
EXPECTED_WRITE_OFFSETS=[0x248,0x250,0x258,0x260]
TARGET_FROM_WHEEL=0x538
RECEIVER_FROM_WHEEL=0x80
TARGET_FROM_RECEIVER=TARGET_FROM_WHEEL-RECEIVER_FROM_WHEEL
INSN_RE=re.compile(r"^\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}\s+)+)\s*([^\s]+)\s*(.*)$")
MEM_RE=re.compile(r"\[ecx\+0x([0-9a-f]+)\]")


def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()


def disassemble(exe:Path)->list[dict]:
 proc=subprocess.run([
  'objdump','-d','-Mintel',f'--start-address=0x{START:x}',f'--stop-address=0x{START+SIZE:x}',str(exe)
 ],check=True,capture_output=True,text=True)
 rows=[]
 for line in proc.stdout.splitlines():
  m=INSN_RE.match(line)
  if not m:continue
  rows.append({'address':int(m.group(1),16),'bytes':bytes.fromhex(m.group(2)),'mnemonic':m.group(3).lower(),'operands':m.group(4).strip().lower()})
 return rows


def analyze(exe:Path)->dict:
 digest=sha256(exe)
 if digest!=PE_SHA256:raise ValueError(f'unexpected retail executable SHA-256: {digest}')
 rows=disassemble(exe);blob=b''.join(r['bytes'] for r in rows);machine_hash=hashlib.sha256(blob).hexdigest()
 if len(blob)!=SIZE or machine_hash!=MACHINE_SHA256:
  raise ValueError(f'FUN_007555b0 machine body drift: bytes={len(blob)} sha={machine_hash}')
 memory=[];writes=[];calls=[];ecx_value_mutations=[]
 for row in rows:
  if row['mnemonic'].startswith('call'):calls.append(f"0x{row['address']:08x}")
  for match in MEM_RE.finditer(row['operands']):
   off=int(match.group(1),16);memory.append(off)
   first=row['operands'].split(',',1)[0].strip()
   if '[ecx+' in first and row['mnemonic'] in {'mov','fst','fstp'}:
    writes.append(off)
  dst=row['operands'].split(',',1)[0].strip() if row['operands'] else ''
  if dst=='ecx' and row['mnemonic'] in {'mov','lea','add','sub','and','or','xor','inc','dec'}:
   ecx_value_mutations.append(f"0x{row['address']:08x} {row['mnemonic']} {row['operands']}")
 unique_memory=sorted(set(memory));unique_writes=sorted(set(writes))
 if unique_memory!=EXPECTED_MEMORY_OFFSETS:raise ValueError(f'ECX memory surface drift: {unique_memory!r}')
 if unique_writes!=EXPECTED_WRITE_OFFSETS:raise ValueError(f'ECX write surface drift: {unique_writes!r}')
 if calls:raise ValueError(f'unexpected direct call(s): {calls!r}')
 if ecx_value_mutations:raise ValueError(f'callee reconstructs/replaces receiver ECX: {ecx_value_mutations!r}')
 if TARGET_FROM_RECEIVER in unique_memory:raise ValueError('selected target unexpectedly addressed from interior receiver')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1D / P1.3D',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':digest,'machine_bytes_adjudicate':True},
  'path':{
   'caller':'FUN_00755950','callsite':'0x00755983','callee':'FUN_007555b0',
   'callee_receiver':'selected wheel+0x80','selected_slot3_wheel':'HDVehicle+0x2380',
   'callee_receiver_absolute':'HDVehicle+0x2400','selected_target_from_wheel':'+0x538',
   'selected_target_from_callee_receiver':'+0x4b8'
  },
  'callee':{
   'start':'0x007555b0','size':SIZE,'instruction_count':len(rows),'machine_bytes_sha256':machine_hash,
   'receiver_register':'ECX','receiver_relative_memory_offsets':[f'+0x{x:x}' for x in unique_memory],
   'receiver_relative_write_offsets':[f'+0x{x:x}' for x in unique_writes],
   'selected_target_relative_offset_observed':False,'direct_call_count':0,
   'receiver_value_reconstruction_or_mutation_count':0
  },
  'selected_wheel_write_offsets':[f'+0x{RECEIVER_FROM_WHEEL+x:x}' for x in unique_writes],
  'adjudication':{
   'fun007555b0_wheel_80_interior_alias_subset_complete':True,
   'fun007555b0_reconstructs_exact_wheel_root':False,
   'fun007555b0_selected_slot3_target_writer_found':False,
   'fun007555b0_forwards_interior_or_reconstructed_root_to_callee':False,
   'other_callee_created_aliases_ruled_out':False,
   'callee_created_aliases_ruled_out':False,
   'stored_or_escaped_aliases_ruled_out':False,
   'slot3_writer_provenance_proven':False,'p1_3d_complete':False,
   'p1_3_control_producer_complete':False,'external_provider_count':7
  },
  'limits':[
   'This closes only the machine-proven wheel+0x80 interior receiver passed from FUN_00755950 to FUN_007555b0.',
   'Other interior/child/callee-created aliases remain independent until their receiver identity and complete machine body are bounded.',
   'No numeric offset coincidence is promoted to selected-wheel identity.'
  ],
  'next_step':'Close remaining transformed-receiver callees and callee-created aliases, then compose with the 16-carrier source-storage and persistence closures.'
 }


def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('exe',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=analyze(a.exe)
 except (ValueError,subprocess.CalledProcessError) as e:p.error(str(e))
 text=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(text,encoding='utf-8')
 else:print(text,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())
