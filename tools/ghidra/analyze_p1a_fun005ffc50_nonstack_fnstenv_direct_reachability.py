#!/usr/bin/env python3
"""Bound direct-control-flow reachability of the two non-stack FNSTENV decodes."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50NonStackFnstenvDirectReachability/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50FnstenvStackRestore/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TEXT_VA,TEXT_RAW=0x00401000,0x400
SITES=[0x004177e4,0x0050d063]
TABLE_RANGE=(0x004177e4,0x00417810,'9a817be1f31c12cb0a5a79c7575f0ba684ced9e51a42943ed5b208c24880fbb5')
PAD_RANGE=(0x0050d035,0x0050d070,'020aacab70bd13f9f9bf551024cd02f41c6552cabeea54d771789a00ca745696')
TABLE_DWORDS=[0x004177d9,0x004175e3,0x004175e3,0x00417630,0x004175d7,0x00417654,0x0041768b,0x0041774b,0x00417768,0x004177a8,0x004177cc]
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def direct_target(op):
 try:return int(op,16)
 except:return None
def incoming(rows,targets):
 d={x:[] for x in targets}
 for a,m,o in rows:
  if not (m=='call' or m=='jmp' or m.startswith('j') or m.startswith('loop')):continue
  t=direct_target(o)
  if t in d:d[t].append({'site':f'0x{a:08x}','kind':m})
 return d
def slice_text(blob,s,e):return blob[TEXT_RAW+s-TEXT_VA:TEXT_RAW+e-TEXT_VA]
def analyze(exe:Path,upstream:Path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 if not up.get('adjudication',{}).get('p13a_fun005ffc50_fnstenv_stack_restore_subset_complete'):raise AssertionError('upstream fnstenv subset incomplete')
 inv=up['fnstenv_inventory']['rows'];non=[x for x in inv if x['operand']!='[esp]']
 if [x['site'] for x in non]!=['0x004177e4','0x0050d063']:raise AssertionError(('non-stack inventory drift',non))
 rows=dis(exe);M={a:(m,o) for a,m,o in rows};inc=incoming(rows,SITES)
 if any(inc.values()):raise AssertionError(('direct incoming edge appeared',inc))
 if M.get(0x004177e2)!=('ret',''):raise AssertionError(('pre-table ret drift',M.get(0x004177e2)))
 if M.get(0x0050d030)!=('jmp','0x4eb550') or M.get(0x0050d070)!=('jmp','0x40cc70'):raise AssertionError('padding boundary drift')
 ts,te,th=TABLE_RANGE;table=slice_text(blob,ts,te);got=hashlib.sha256(table).hexdigest()
 if got!=th or len(table)!=te-ts:raise AssertionError(('table range drift',got))
 dws=list(struct.unpack('<'+'I'*(len(table)//4),table))
 if dws!=TABLE_DWORDS:raise AssertionError(('table dwords drift',dws))
 ps,pe,ph=PAD_RANGE;pad=slice_text(blob,ps,pe);pg=hashlib.sha256(pad).hexdigest()
 if pg!=ph or len(pad)!=pe-ps:raise AssertionError(('padding range drift',pg))
 noncc=[(ps+i,b) for i,b in enumerate(pad) if b!=0xcc]
 expected_noncc=[(0x0050d035,0x90),(0x0050d063,0xd9),(0x0050d064,0xb3)]
 if noncc!=expected_noncc:raise AssertionError(('padding bytes drift',noncc))
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM,
   'machine_ranges':{
    'aligned_code_pointer_table':{'start':f'0x{ts:08x}','end_exclusive':f'0x{te:08x}','size':te-ts,'sha256':got},
    'int3_padding_window':{'start':f'0x{ps:08x}','end_exclusive':f'0x{pe:08x}','size':pe-ps,'sha256':pg}}},
  'non_stack_fnstenv_rows':non,
  'direct_incoming_edges':{f'0x{k:08x}':v for k,v in inc.items()},
  'decode_0x004177e4_context':{'preceded_by':'0x004177e2 ret','aligned_dword_count':len(dws),'aligned_dwords':[f'0x{x:08x}' for x in dws],'all_dwords_point_into_nearby_text':all(0x00417500<=x<0x00417800 for x in dws)},
  'decode_0x0050d063_context':{'window_start':'0x0050d035','window_end_exclusive':'0x0050d070','size':len(pad),'int3_byte_count':pad.count(0xcc),'non_int3_bytes':[{'site':f'0x{a:08x}','byte':f'0x{b:02x}'} for a,b in noncc],'preceding_transfer':'0x0050d030 jmp 0x4eb550','following_transfer':'0x0050d070 jmp 0x40cc70'},
  'adjudication':{
   'p13a_fun005ffc50_nonstack_fnstenv_direct_reachability_subset_complete':True,
   'nonstack_fnstenv_direct_call_or_branch_entry_found':False,
   'nonstack_fnstenv_fallthrough_from_preceding_code_found':False,
   'nonstack_fnstenv_indirect_or_runtime_entry_ruled_out':False,
   'other_pic_or_fnstenv_entry_ruled_out':False,
   'writable_memory_or_runtime_fun005ffc50_entry_ruled_out':False,
   'encoded_or_reconstructed_callback_entry_ruled_out':False,
   'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,
   'fun0067b660_callback_argument_provenance_complete':False,
   'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
   'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':[
   'This closes only direct call/jmp/jcc/loop entry and ordinary fallthrough into the two non-stack FNSTENV decode addresses.',
   'At 0x004177e4 the bytes form eleven aligned little-endian dwords pointing into nearby .text and begin immediately after a RET; this is strong table-shaped machine evidence but not a universal proof against arbitrary indirect entry.',
   'At 0x0050d063 the decode sits in a 59-byte padding window containing 56 INT3 bytes, bounded by an earlier unconditional JMP and the next trampoline JMP; arbitrary indirect/runtime entry into the middle remains unruled.',
   'Writable-memory callbacks, indirect computed jumps, inter-block/return-value reconstruction and runtime-generated pointers remain open.',
   'No global callback, reconstructed-entry, slot0, slot1, stored-alias, runtime selected-wheel-store-negative or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Move P1.3A FUN_005ffc50 entry work to writable-memory/runtime callback slots and inter-block/return-value provenance; all four retail FNSTENV decodes now have bounded direct/static classifications.'
 }
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
