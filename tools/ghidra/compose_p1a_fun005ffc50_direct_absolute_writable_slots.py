#!/usr/bin/env python3
"""Compose all direct absolute .data indirect-transfer slots relevant to FUN_005ffc50."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50DirectAbsoluteWritableTransferComposition/1'
PAIR='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairStaticProvenance/1'
NVAPI='SHIFT.P1A.P13AFun005ffc50NvapiWritableDispatchTable/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET=0x005ffc50
DATA_VA,DATA_END,DATA_RAW=0x00b81000,0x00bbc600,0x0077f600
FIXED={0x00b87b64:0x00901707,0x00b87b68:0x0090162a}
PAIR_SLOTS={0x00b87b7c,0x00b87b80}
NV_START,NV_COUNT,NV_STRIDE=0x00bbbd0c,255,8
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True);out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def dword(blob,va):return struct.unpack_from('<I',blob,DATA_RAW+va-DATA_VA)[0]
def abs_writable_xfers(rows):
 out=[]
 for a,m,o in rows:
  if m not in {'call','jmp'}:continue
  mm=re.fullmatch(r'DWORD PTR ds:0x([0-9a-f]+)',o)
  if not mm:continue
  s=int(mm.group(1),16)
  if DATA_VA<=s<DATA_END:out.append((a,m,s))
 return out
def abs_writes(rows,slot):
 needle=f'0x{slot:x}';out=[]
 for a,m,o in rows:
  if ',' not in o:continue
  d=o.split(',',1)[0]
  if needle in d and m not in {'cmp','test'}:out.append((a,m,o))
 return out
def load(path,fmt):
 p=json.loads(path.read_text(encoding='utf-8'))
 if p.get('format')!=fmt or not p.get('ready'):raise ValueError((path,p.get('format'),p.get('ready')))
 return p
def analyze(exe:Path,pair_path:Path,nvapi_path:Path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 pair=load(pair_path,PAIR);nv=load(nvapi_path,NVAPI)
 if not pair['adjudication']['p13a_fun005ffc50_writable_callback_pair_direct_static_provenance_subset_complete']:raise AssertionError('pair incomplete')
 if not nv['adjudication']['p13a_fun005ffc50_nvapi_writable_dispatch_table_subset_complete']:raise AssertionError('nvapi incomplete')
 rows=dis(exe);x=abs_writable_xfers(rows);slots=sorted({s for _,_,s in x})
 nvslots={NV_START+i*NV_STRIDE for i in range(NV_COUNT)}
 expected=set(FIXED)|PAIR_SLOTS|nvslots
 if set(slots)!=expected or len(slots)!=259 or len(x)!=334:raise AssertionError(('writable xfer inventory drift',len(slots),len(x),set(slots)^expected))
 fixed_rows={}
 for s,v in FIXED.items():
  if dword(blob,s)!=v:raise AssertionError(('fixed initial drift',hex(s),hex(dword(blob,s))))
  sx=[(a,m) for a,m,ss in x if ss==s]
  wr=abs_writes(rows,s)
  if len(sx)!=1 or sx[0][1]!='jmp' or wr:raise AssertionError(('fixed surface drift',hex(s),sx,wr))
  fixed_rows[f'0x{s:08x}']={'initial_target':f'0x{v:08x}','direct_transfer_count':1,'direct_transfer_kind':'jmp','direct_absolute_writer_count':0,'targets_FUN_005ffc50':v==TARGET}
 pair_transfer=sum(1 for _,_,s in x if s in PAIR_SLOTS);nv_transfer=sum(1 for _,_,s in x if s in nvslots);fixed_transfer=sum(1 for _,_,s in x if s in FIXED)
 if (pair_transfer,nv_transfer,fixed_transfer)!=(77,255,2):raise AssertionError(('group counts',pair_transfer,nv_transfer,fixed_transfer))
 if pair['writable_callback_pair']['direct_static_candidate_values_include_FUN_005ffc50']:raise AssertionError('pair target drift')
 if nv['nvapi_table']['game_internal_FUN_005ffc50_static_provider_present']:raise AssertionError('nvapi internal provider drift')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'input_contracts':{'callback_pair':PAIR,'nvapi_table':NVAPI}},
  'direct_absolute_writable_transfer_inventory':{
   'data_start':'0x00b81000','data_end_exclusive':'0x00bbc600','unique_slot_count':len(slots),'transfer_count':len(x),
   'groups':{
    'nvapi_queryinterface_table':{'slot_count':255,'transfer_count':nv_transfer,'internal_FUN_005ffc50_provider_found':False},
    'writable_callback_pair':{'slot_count':2,'transfer_count':pair_transfer,'direct_static_FUN_005ffc50_value_found':False},
    'fixed_bridge_slots':{'slot_count':2,'transfer_count':fixed_transfer,'rows':fixed_rows},
   },
   'all_unique_slots_partitioned':True,'bounded_internal_FUN_005ffc50_provider_found':False,
  },
  'adjudication':{
   'p13a_fun005ffc50_direct_absolute_writable_indirect_transfer_slot_inventory_complete':True,
   'direct_absolute_writable_transfer_internal_fun005ffc50_provider_found':False,
   'register_loaded_or_aliased_writable_slots_ruled_out':False,
   'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
   'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,
   'return_value_fun005ffc50_provenance_ruled_out':False,'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,
   'encoded_or_reconstructed_callback_entry_ruled_out':False,'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,'fun0067b660_callback_argument_provenance_complete':False,
   'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
   'This composes only direct machine transfers of the form call/jmp DWORD PTR ds:<absolute address> where the slot lies in the retail .data section.',
   'Register-loaded writable pointers, base/index-addressed slots, alias writes, heap/runtime-generated pointers and arbitrary external mutation remain open.',
   'The NVAPI group is external-provider infrastructure; the callback pair is only direct/static-closed; the two fixed bridge slots have no direct absolute writers.',
   'No global writable-memory, callback, reconstructed-entry, slot0, slot1, stored-alias or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Focus writable-memory work on register-loaded/base-indexed/aliased sources; all direct absolute .data indirect-transfer slots are now partitioned and bounded.'
 }
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--pair',type=Path,required=True);ap.add_argument('--nvapi',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.pair,a.nvapi);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
