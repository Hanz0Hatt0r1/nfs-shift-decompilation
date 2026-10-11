#!/usr/bin/env python3
"""Bound direct/static provenance of writable callback slots 0x00b87b7c/0x00b87b80."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairStaticProvenance/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50TrivialConstantReturnProducers/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET=0x005ffc50
DATA_VA,DATA_RAW=0x00b81000,0x0077f600
RDATA_VA,RDATA_RAW=0x00aa6000,0x006a4a00
SLOT_A=0x00b87b80; SLOT_B=0x00b87b7c
DEF_A=0x00be87dc; DEF_B=0x00be87e0
SETTER=0x00616687; CONFIG=0x0060ad99
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True);out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def dword(blob,va,section):
 base,raw=(DATA_VA,DATA_RAW) if section=='data' else (RDATA_VA,RDATA_RAW)
 return struct.unpack_from('<I',blob,raw+va-base)[0]
def occurrences(blob,v):
 p=struct.pack('<I',v);out=[];i=0
 while True:
  i=blob.find(p,i)
  if i<0:return out
  out.append(i);i+=1
def direct_calls(rows,t):return [a for a,m,o in rows if m=='call' and o==f'0x{t:x}']
def slot_xfers(rows,slot):
 needle=f'DWORD PTR ds:0x{slot:x}'
 return [(a,m) for a,m,o in rows if m in {'call','jmp'} and o==needle]
def slot_writes(rows,slot):
 # Exact absolute destination writes only; alias writes remain out of scope.
 needle=f'0x{slot:x}'
 out=[]
 for a,m,o in rows:
  if ',' not in o:continue
  d=o.split(',',1)[0]
  if needle in d and m not in {'cmp','test'}:out.append((a,m,o))
 return out
def req(M,a,m,o):
 got=M.get(a);exp=(m,norm(o))
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {got[0]} {got[1]}'
def analyze(exe:Path,upstream:Path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up.get('adjudication',{}).get('p13a_fun005ffc50_trivial_constant_return_producer_subset_complete'):raise AssertionError('upstream return subset incomplete')
 rows=dis(exe);M={a:(m,o) for a,m,o in rows}
 init_a=dword(blob,SLOT_A,'data');init_b=dword(blob,SLOT_B,'data')
 if (init_a,init_b)!=(0x006165b6,0x006165c0):raise AssertionError(('initial slot drift',hex(init_a),hex(init_b)))
 if dword(blob,0x00aa77b8,'rdata')!=0x00a7fa5c or dword(blob,0x00aa77bc,'rdata')!=0x00a7fa67:raise AssertionError('startup initializer table drift')
 calls_set=direct_calls(rows,SETTER);calls_cfg=direct_calls(rows,CONFIG)
 if calls_set!=[0x0060adde,0x0061ccbe] or calls_cfg!=[0x005f3b7f,0x005f47b7]:raise AssertionError(('call surface drift',calls_set,calls_cfg))
 xa=slot_xfers(rows,SLOT_A);xb=slot_xfers(rows,SLOT_B)
 if len(xa)!=26 or len(xb)!=51:raise AssertionError(('transfer surface drift',len(xa),len(xb)))
 wa=slot_writes(rows,SLOT_A);wb=slot_writes(rows,SLOT_B)
 if [x[0] for x in wa]!=[0x00616602,0x006166c5] or [x[0] for x in wb]!=[0x0061660d,0x006166d8]:raise AssertionError(('writer surface drift',wa,wb))
 for v in (SETTER,CONFIG):
  if occurrences(blob,v) or occurrences(blob,v-0x00400000):raise AssertionError(('address taken drift',hex(v)))
 A={
  'init_snapshot_A':req(M,0x00a7fa5c,'mov','eax,ds:0xb87b80'),
  'init_snapshot_A_store':req(M,0x00a7fa61,'mov','ds:0xbe87dc,eax'),
  'init_snapshot_B':req(M,0x00a7fa67,'mov','eax,ds:0xb87b7c'),
  'init_snapshot_B_store':req(M,0x00a7fa6c,'mov','ds:0xbe87e0,eax'),
  'config_zero_push_1':req(M,0x005f3b7d,'push','eax'),
  'config_zero_push_2':req(M,0x005f3b7e,'push','eax'),
  'config_fixed_B':req(M,0x005f47ad,'push','0x5f4760'),
  'config_fixed_A':req(M,0x005f47b2,'push','0x5f46f0'),
  'config_setter_call':req(M,0x0060adde,'call','0x616687'),
  'setter_fixed_flag_zero':req(M,0x0061ccb3,'push','eax'),
  'setter_fixed_B':req(M,0x0061ccb4,'push','0x61cbff'),
  'setter_fixed_A':req(M,0x0061ccb9,'push','0x61cb43'),
  'setter_call_fixed':req(M,0x0061ccbe,'call','0x616687'),
  'slot_A_default_load':req(M,0x006166c0,'mov','eax,ds:0xbe87dc'),
  'slot_A_store':req(M,0x006166c5,'mov','ds:0xb87b80,eax'),
  'slot_B_default_load':req(M,0x006166d1,'mov','eax,ds:0xbe87e0'),
  'slot_B_store':req(M,0x006166d8,'mov','ds:0xb87b7c,eax'),
 }
 values_a=sorted({init_a,0x005f46f0,0x0061cb43});values_b=sorted({init_b,0x005f4760,0x0061cbff})
 assert TARGET not in values_a and TARGET not in values_b
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},
  'writable_callback_pair':{
   'slot_A':'0x00b87b80','slot_B':'0x00b87b7c','initial_slot_A':f'0x{init_a:08x}','initial_slot_B':f'0x{init_b:08x}',
   'default_snapshot_A':'0x00be87dc','default_snapshot_B':'0x00be87e0',
   'startup_snapshot_table_entries':{'0x00aa77b8':'0x00a7fa5c','0x00aa77bc':'0x00a7fa67'},
   'direct_setter':'FUN_00616687','direct_setter_callsites':[f'0x{x:08x}' for x in calls_set],
   'direct_config':'FUN_0060ad99','direct_config_callsites':[f'0x{x:08x}' for x in calls_cfg],
   'slot_A_direct_indirect_transfer_count':len(xa),'slot_B_direct_indirect_transfer_count':len(xb),
   'slot_A_direct_absolute_writers':[f'0x{x[0]:08x}' for x in wa],'slot_B_direct_absolute_writers':[f'0x{x[0]:08x}' for x in wb],
   'direct_static_slot_A_candidate_values':[f'0x{x:08x}' for x in values_a],
   'direct_static_slot_B_candidate_values':[f'0x{x:08x}' for x in values_b],
   'direct_static_candidate_values_include_FUN_005ffc50':False,
  },
  'machine_anchors':A,
  'static_entry_address_literals':{
   'FUN_00616687_absolute_va_count':0,'FUN_00616687_rva_count':0,
   'FUN_0060ad99_absolute_va_count':0,'FUN_0060ad99_rva_count':0,
  },
  'adjudication':{
   'p13a_fun005ffc50_writable_callback_pair_direct_static_provenance_subset_complete':True,
   'writable_callback_pair_direct_static_fun005ffc50_value_found':False,
   'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,
   'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
   'return_value_fun005ffc50_provenance_ruled_out':False,
   'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,
   'encoded_or_reconstructed_callback_entry_ruled_out':False,
   'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,
   'fun0067b660_callback_argument_provenance_complete':False,
   'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
   'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
   'This closes only direct absolute writers and direct/static entry to FUN_00616687/FUN_0060ad99 for the heavily used writable callback slots 0x00b87b80 and 0x00b87b7c.',
   'The default snapshots are tied to the retail initial slot values through startup initializer entries, but arbitrary alias writes, reconstructed/indirect setter entry, and external/runtime mutation remain open.',
   'Other writable callback slots are not classified by this contract.',
   'No global writable-memory, callback, reconstructed-entry, slot0, slot1, stored-alias or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Trace alias/indirect writers or other writable function-pointer slots; the direct/static producer surface of 0x00b87b80/0x00b87b7c no longer needs to be rescanned.'
 }
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
