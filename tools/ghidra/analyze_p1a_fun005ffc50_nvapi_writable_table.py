#!/usr/bin/env python3
"""Classify the 255-slot writable NVAPI QueryInterface dispatch table."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50NvapiWritableDispatchTable/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairStaticProvenance/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET=0x005ffc50
DATA_VA,DATA_RAW=0x00b81000,0x0077f600
RDATA_VA,RDATA_RAW=0x00aa6000,0x006a4a00
TABLE=0x00bbbd0c; COUNT=255; STRIDE=8; STUB=0x00a61a48; TERM=0x00bbc504
THUNK_FIRST=0x00a61ae8; THUNK_STRIDE=6
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True);out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def dword(blob,va,sec='data'):
 base,raw=(DATA_VA,DATA_RAW) if sec=='data' else (RDATA_VA,RDATA_RAW)
 return struct.unpack_from('<I',blob,raw+va-base)[0]
def cstr(blob,va):
 off=RDATA_RAW+va-RDATA_VA;end=blob.index(0,off);return blob[off:end].decode('ascii')
def req(M,a,m,o):
 got=M.get(a);exp=(m,norm(o))
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {got[0]} {got[1]}'
def analyze(exe:Path,upstream:Path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up.get('adjudication',{}).get('p13a_fun005ffc50_writable_callback_pair_direct_static_provenance_subset_complete'):raise AssertionError('upstream writable pair incomplete')
 rows=dis(exe);M={a:(m,o) for a,m,o in rows}
 ptrs=[dword(blob,TABLE+i*STRIDE) for i in range(COUNT)]
 ids=[dword(blob,TABLE+i*STRIDE+4) for i in range(COUNT)]
 if set(ptrs)!={STUB}:raise AssertionError(('initial table pointer drift',set(ptrs)))
 if len(set(ids))!=COUNT or 0 in ids:raise AssertionError('NVAPI ID uniqueness/zero drift')
 if dword(blob,TERM)!=0:raise AssertionError('table terminator drift')
 if cstr(blob,0x00b66b10)!='nvapi.dll' or cstr(blob,0x00b66b1a)!='nvapi_QueryInterface':raise AssertionError('NVAPI strings drift')
 thunks=[]
 for i in range(COUNT):
  a=THUNK_FIRST+i*THUNK_STRIDE;slot=TABLE+i*STRIDE
  exp=f'DWORD PTR ds:0x{slot:x}'
  if M.get(a)!=('jmp',exp):raise AssertionError(('thunk drift',i,hex(a),M.get(a),exp))
  thunks.append(a)
 xfers=[]
 for a,m,o in rows:
  if m not in {'call','jmp'}:continue
  mm=re.fullmatch(r'DWORD PTR ds:0x([0-9a-f]+)',o)
  if not mm:continue
  s=int(mm.group(1),16)
  if TABLE<=s<TABLE+COUNT*STRIDE and (s-TABLE)%STRIDE==0:xfers.append((a,m,s))
 if len(xfers)!=COUNT or any(m!='jmp' for _,m,_ in xfers):raise AssertionError(('NVAPI xfer inventory drift',len(xfers)))
 A={
  'load_library_name':req(M,0x00a61a5b,'push','0xb66b10'),
  'load_library_call':req(M,0x00a61a60,'call','DWORD PTR ds:0xaa6300'),
  'query_interface_name':req(M,0x00a61a76,'push','0xb66b1a'),
  'get_proc_address_call':req(M,0x00a61a7c,'call','DWORD PTR ds:0xaa62fc'),
  'save_query_interface':req(M,0x00a61a86,'mov','ebp,eax'),
  'initialize_id':req(M,0x00a61a88,'push','0x150e828'),
  'query_initialize':req(M,0x00a61a8d,'call','ebp'),
  'call_initialize':req(M,0x00a61a94,'call','eax'),
  'table_base':req(M,0x00a61aae,'mov','esi,0xbbbd0c'),
  'load_id':req(M,0x00a61ab3,'mov','eax,DWORD PTR [esi+0x4]'),
  'terminator_test':req(M,0x00a61ab6,'test','eax,eax'),
  'push_id':req(M,0x00a61aba,'push','eax'),
  'query_entry':req(M,0x00a61abb,'call','ebp'),
  'store_resolved_pointer':req(M,0x00a61ac2,'mov','DWORD PTR [esi],eax'),
  'next_record':req(M,0x00a61ac4,'add','esi,0x8'),
  'stub_status_load':req(M,0x00a61a48,'mov','eax,ds:0xbbbd08'),
 }
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM},
  'nvapi_table':{
   'module_name':'nvapi.dll','query_symbol':'nvapi_QueryInterface','table_start':'0x00bbbd0c','record_stride':8,'record_count':COUNT,
   'pointer_field_offset':0,'function_id_field_offset':4,'terminator_id_address':'0x00bbc504','terminator_id_value':0,
   'initial_pointer':'0x00a61a48','initial_pointer_count':ptrs.count(STUB),'unique_function_id_count':len(set(ids)),'zero_function_id_count':ids.count(0),
   'known_anchor_function_id':'0xe5ac921f','known_anchor_index':ids.index(0xe5ac921f),
   'first_function_id':f'0x{ids[0]:08x}','last_function_id':f'0x{ids[-1]:08x}',
   'direct_thunk_count':len(thunks),'direct_table_indirect_transfer_count':len(xfers),
   'first_thunk':f'0x{thunks[0]:08x}','last_thunk':f'0x{thunks[-1]:08x}',
   'resolution_value_class':['initial internal failure/status stub 0x00a61a48','nonzero pointer returned by external nvapi_QueryInterface'],
   'game_internal_FUN_005ffc50_static_provider_present':False,
  },
  'machine_anchors':A,
  'adjudication':{
   'p13a_fun005ffc50_nvapi_writable_dispatch_table_subset_complete':True,
   'nvapi_writable_table_internal_fun005ffc50_static_provider_found':False,
   'nvapi_writable_table_values_are_stub_or_external_queryinterface_results':True,
   'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
   'writable_callback_pair_indirect_or_alias_writers_ruled_out':False,
   'return_value_fun005ffc50_provenance_ruled_out':False,
   'unbounded_multi_edge_or_phi_reconstruction_ruled_out':False,
   'encoded_or_reconstructed_callback_entry_ruled_out':False,
   'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,
   'fun0067b660_callback_argument_provenance_complete':False,
   'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
   'This classifies exactly the 255-record NVAPI QueryInterface table at 0x00bbbd0c and its direct thunk surface.',
   'Resolved nonzero values are produced by the external nvapi_QueryInterface provider; this is not a proof about arbitrary writable slots elsewhere.',
   'Loader/module replacement, hostile external provider behavior, unrelated writable aliases and other runtime-generated pointers remain outside this bounded contract.',
   'No global writable-memory, callback, reconstructed-entry, slot0, slot1, stored-alias or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'After excluding the NVAPI table and the b87b7c/b87b80 pair, inventory any remaining writable function-pointer sources or return/phi provenance relevant to FUN_005ffc50.'
 }
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
