#!/usr/bin/env python3
"""Bound direct call-next/pop PIC reconstruction relevant to FUN_005ffc50."""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun005ffc50CallNextPic/1'
UPSTREAM='SHIFT.P1A.P13AFun005ffc50StaticMemoryStackReconstruction/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET=0x005ffc50
CALLNEXT=0x00d31404
RETURN=0x00d31409
PIC_BASE=0x00d31000
RANGE=(0x00d31400,0x00d31422,0x00d31000,0x00801c00,'e1890a43eb24c8e35b25f6847e8d343902d22d0a7adb08395c3fcf67d105e112')
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def rows(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def direct_target(op):
 try:return int(op,16)
 except:return None
def find_callnext(rs):
 out=[]
 for i,(a,m,o) in enumerate(rs[:-1]):
  if m!='call':continue
  n=rs[i+1][0];t=direct_target(o)
  if t==n:out.append({'call':f'0x{a:08x}','return':f'0x{n:08x}','next_instruction':f'{rs[i+1][1]} {rs[i+1][2]}'.rstrip()})
 return out
def analyze(exe,upstream):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM:raise ValueError(up.get('format'))
 a=up.get('adjudication',{})
 if not a.get('p13a_fun005ffc50_readonly_image_and_explicit_stack_reconstruction_subset_complete'):raise AssertionError('upstream subset incomplete')
 rs=rows(exe);cn=find_callnext(rs)
 exp=[{'call':'0x00d31404','return':'0x00d31409','next_instruction':'pop ebp'}]
 if cn!=exp:raise AssertionError(('call-next surface drift',cn))
 M={x[0]:(x[1],x[2]) for x in rs}
 anchors={
  'push_flags':'0x00d31400 pushf',
  'call_next':'0x00d31404 call 0xd31409',
  'capture_return':'0x00d31409 pop ebp',
  'subtract_delta':'0x00d3140a sub ebp,0x409',
  'copy_pic_base':'0x00d3141a mov ebx,ebp',
  'first_control_boundary':'0x00d31420 je 0xd3142b',
 }
 checks={0xd31400:('pushf',''),0xd31404:('call','0xd31409'),0xd31409:('pop','ebp'),0xd3140a:('sub','ebp,0x409'),0xd3141a:('mov','ebx,ebp'),0xd31420:('je','0xd3142b')}
 for q,w in checks.items():
  if M.get(q)!=w:raise AssertionError((hex(q),M.get(q),w))
 s,e,base,raw,h=RANGE;chunk=blob[raw+s-base:raw+e-base]
 got=hashlib.sha256(chunk).hexdigest()
 if len(chunk)!=e-s or got!=h:raise AssertionError(('range drift',len(chunk),got))
 derived=(RETURN-0x409)&0xffffffff
 if derived!=PIC_BASE or derived==TARGET:raise AssertionError(('PIC derivation drift',hex(derived)))
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM,
    'machine_range':{'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':got}},
  'call_next_surface':{'decoded_instruction_count':len(rs),'call_next_count':1,'rows':cn},
  'pic_candidate':{'call':'0x00d31404','captured_return':'0x00d31409','operation':'sub ebp,0x409','derived_value':'0x00d31000','derived_value_is_fun005ffc50':False,'first_control_boundary':'0x00d31420'},
  'machine_anchors':anchors,
  'adjudication':{
   'p13a_fun005ffc50_call_next_pop_pic_subset_complete':True,
   'call_next_pop_fun005ffc50_reconstruction_found':False,
   'call_next_pop_fun005ffc50_indirect_entry_found':False,
   'other_pic_or_fnstenv_entry_ruled_out':False,
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
   'This closes only the exact direct call-to-next-instruction / pop-register EIP acquisition class present in the retail image.',
   'The sole call-next site derives 0x00d31000 before its first conditional branch, not FUN_005ffc50 at 0x005ffc50.',
   'FPU-environment EIP acquisition, inter-block arithmetic, writable-memory callback slots, return-value provenance, encoded/split values, and runtime-generated pointers remain open.',
   'No global reconstructed-entry, callback, slot0, slot1, stored-alias, runtime selected-wheel-store-negative, or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Trace writable-memory/runtime callback slots, FPU-environment or other inter-block entry to FUN_005ffc50; direct/raw, simple GPR, read-only image, explicit stack-local and call-next/pop PIC subsets are now bounded.'
 }
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--upstream',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
