#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT='SHIFT.P1D.Slot3MachineWheelRootMaterializationClosure/1'
PE_SHA256='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
WHEEL_OFFSETS=[0x400,0xe80,0x1900,0x2380]
LOOP=(0x007635f4,0x0076362a,'30ae593298ee11283898a0397b527583fc232d3db7ac4f0db7a8578e6bf00333')
EXPLICIT=(0x007710fe,0x00771185,'9007ea4422621778fa979ae4ca105faa85f1f03b792803da7f6d3b34d38c6534')
INSN_RE=re.compile(r'^\s*([0-9a-fA-F]+):\s*((?:[0-9a-fA-F]{2}\s+)+)\s*([^\s]+)\s*(.*)$')

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def disasm(exe:Path,s:int,e:int):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],check=True,capture_output=True,text=True)
 rows=[]
 for line in p.stdout.splitlines():
  m=INSN_RE.match(line)
  if m: rows.append({'address':int(m.group(1),16),'bytes':bytes.fromhex(m.group(2)),'mnemonic':m.group(3).lower(),'operands':m.group(4).strip().lower()})
 return rows

def pin(rows,expected):
 blob=b''.join(r['bytes'] for r in rows); digest=hashlib.sha256(blob).hexdigest()
 if digest!=expected: raise ValueError(f'window drift: {digest}')
 return {'instruction_count':len(rows),'decoded_byte_count':len(blob),'machine_bytes_sha256':digest}

def rowmap(rows): return {r['address']:(r['mnemonic'],r['operands']) for r in rows}

def require(m,a,mn,ops):
 got=m.get(a)
 if got!=(mn,ops): raise ValueError(f'0x{a:08x} drift: {got!r}')

def analyze(exe:Path):
 digest=sha256(exe)
 if digest!=PE_SHA256: raise ValueError(f'unexpected retail executable SHA-256: {digest}')
 lr=disasm(exe,LOOP[0],LOOP[1]); er=disasm(exe,EXPLICIT[0],EXPLICIT[1])
 lp=pin(lr,LOOP[2]); ep=pin(er,EXPLICIT[2]); lm=rowmap(lr); em=rowmap(er)
 require(lm,0x007635f4,'lea','eax,[edi+0x400]')
 require(lm,0x00763609,'mov','dword ptr [ebp-0x4],eax')
 require(lm,0x0076360c,'mov','ecx,dword ptr [ebp-0x4]')
 require(lm,0x0076360f,'call','0x755f80')
 require(lm,0x0076361b,'add','dword ptr [ebp-0x4],0xa80')
 require(lm,0x00763622,'add','esi,0x1')
 require(lm,0x00763625,'cmp','esi,0x4')
 require(lm,0x00763628,'jl','0x76360c')
 for a,off in [(0x007710fe,0x400),(0x0077111c,0xe80),(0x00771138,0x1900),(0x00771177,0x2380)]:
  require(em,a,'lea',f'ecx,[esi+0x{off:x}]')
 for a in [0x00771107,0x00771125,0x00771147,0x00771162,0x00771180]: require(em,a,'call','0x760b50')
 for start,end in [(0x007710fe,0x00771107),(0x0077111c,0x00771125),(0x00771138,0x00771147),(0x00771155,0x00771162),(0x00771177,0x00771180)]:
  for r in er:
   if not (start < r['address'] < end): continue
   if r['mnemonic']=='push' and r['operands']=='ecx': raise ValueError(f'wheel-root push before consumer: {r!r}')
   if r['mnemonic']=='mov' and r['operands'].endswith(',ecx') and '[' in r['operands'].split(',',1)[0]: raise ValueError(f'wheel-root store before consumer: {r!r}')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1D / P1.3D',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':digest,'machine_bytes_adjudicate':True},
  'selected_slot3':{'wheel_receiver':'HDVehicle+0x2380','local_target':'+0x538','absolute_target':'HDVehicle+0x28b8..+0x28bf'},
  'wheel_layout':{'root_offsets':[f'+0x{x:x}' for x in WHEEL_OFFSETS],'stride':'+0xa80','count':4},
  'fun00763570_loop':{'window':{'start':'0x007635f4','end_exclusive':'0x0076362a',**lp},'seed':'0x007635f4 EAX = HDVehicle+0x400','cursor_storage':'stack-local [EBP-0x4]','consumer':'FUN_00755f80','callsite':'0x0076360f','stride_update':'0x0076361b [EBP-0x4] += 0xa80','iteration_test':'0x00763625 ESI == 4','materialized_receivers':[f'HDVehicle+0x{x:x}' for x in WHEEL_OFFSETS],'nonstack_wheel_root_store_found':False},
  'fun00770e80_explicit':{'window':{'start':'0x007710fe','end_exclusive':'0x00771185',**ep},'callee':'FUN_00760b50','materializations':[{'site':'0x007710fe','receiver':'HDVehicle+0x400','calls':['0x00771107']},{'site':'0x0077111c','receiver':'HDVehicle+0xe80','calls':['0x00771125']},{'site':'0x00771138','receiver':'HDVehicle+0x1900','calls':['0x00771147','0x00771162'],'note':'branch alternatives reuse the same ECX receiver'},{'site':'0x00771177','receiver':'HDVehicle+0x2380','calls':['0x00771180'],'selected_slot3':True}],'wheel_root_push_count':0,'wheel_root_nonstack_store_count':0},
  'adjudication':{'known_hdvehicle_to_four_wheel_root_materialization_machine_subset_complete':True,'selected_slot3_wheel_root_materialization_proven':True,'selected_slot3_wheel_root_nonstack_persistence_found':False,'selected_slot3_wheel_root_new_forward_beyond_closed_consumers_found':False,'other_derived_alias_storage_ruled_out':False,'runtime_generated_pointer_stores_ruled_out':False,'callbacks_registered_outside_carriers_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'slot3_writer_provenance_proven':False,'p1_3d_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['This closes only the two already-machine-identified HDVehicle-to-wheel-root materialization paths in FUN_00763570 and FUN_00770e80.','Interior/child aliases, reconstructed pointers from memory, aggregate copies, callbacks, indirect entry and runtime-generated/copied/encoded pointers remain separate.','The loop cursor is stack-local; no numeric offset coincidence is promoted to object identity.'],
  'next_step':'Trace remaining derived/interior aliases that can persist or be reconstructed from memory, then compose callback/indirect-entry evidence before changing stored-or-escaped-alias gates.'
 }

def main():
 p=argparse.ArgumentParser(); p.add_argument('exe',type=Path); p.add_argument('--output',type=Path); a=p.parse_args()
 try:r=analyze(a.exe)
 except (ValueError,subprocess.CalledProcessError) as e:p.error(str(e))
 t=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(t,encoding='utf-8')
 else: print(t,end='')
if __name__=='__main__': main()
