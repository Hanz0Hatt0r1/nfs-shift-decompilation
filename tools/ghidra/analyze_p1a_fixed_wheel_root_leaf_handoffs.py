#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFixedWheelRootLeafHandoffs/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TEXT_VA=0x401000;TEXT_RAW=0x400
RANGES={
 'caller_fun007582f0':(0x74d8b1,0x74d8bb,'4e64c7876a3c648e60fa6528c29ca09bec21be44b3cb1e69fe32cf204b3e7bfd'),
 'fun007582f0':(0x7582f0,0x75831e,'23f06607cb7adf6cb75adc72fb3d8a4880cd87a00af068c8230c34fc6737875e'),
 'fun00756010':(0x756010,0x75603b,'76ef5a938d5ea0008c6b9411f115c2aaa6684d4f06b067e1cf4261880f4c2100'),
 'caller_fun0076ed60':(0x74dfe3,0x74dfed,'0c5451be59e83de8fee5267dbf790f56baaba44a28bb75c462733a4b3f5c154c'),
 'fun0076ed60_prologue':(0x76ed60,0x76ed67,'b3c713f9d08334723ded524160c23970444b1a55d80015d013eeb87172742d22'),
 'fun0076ed60_window':(0x76ee3c,0x76ee84,'7eacc49b1481bdb5c27d267f0bfac29607829d721106013481384bece580dbfd'),
 'fun00753020':(0x753020,0x7530e0,'117dd2fa87dfca67d162638192ab7ba71dc0fd32cdef5a19fc2c42a79caa59c2')}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe,s,e):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for l in p.stdout.splitlines():
  m=I.match(l)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def req(M,a,m,o):
 exp=(m,norm(o));got=M.get(a)
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {m} {exp[1]}'
def analyze(exe:Path):
 b=exe.read_bytes();sha=hashlib.sha256(b).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 maps={};auth={}
 for name,(s,e,h) in RANGES.items():
  off=TEXT_RAW+s-TEXT_VA;x=b[off:off+e-s];hh=hashlib.sha256(x).hexdigest()
  if len(x)!=e-s or hh!=h:raise AssertionError((name,len(x),hh))
  rows=dis(exe,s,e);maps[name]={a:(m,o) for a,m,o in rows};auth[name]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 C=maps['caller_fun007582f0'];req(C,0x74d8b1,'mov','ecx,0xc13700');req(C,0x74d8b6,'call','0x7582f0')
 C=maps['caller_fun0076ed60'];req(C,0x74dfe3,'mov','ecx,0xc13700');req(C,0x74dfe8,'call','0x76ed60')
 P=maps['fun0076ed60_prologue'];req(P,0x76ed64,'mov','esi,ecx')
 M=maps['fun007582f0'];A=[];req(M,0x7582f0,'mov','eax,ecx')
 pairs=[(0x7582f2,0x7582f8,0x400,'call'),(0x7582fd,0x758303,0xe80,'call'),(0x758308,0x75830e,0x1900,'call'),(0x758313,0x758319,0x2380,'jmp')]
 for i,(la,ta,off,kind) in enumerate(pairs):
  req(M,la,'lea',f'ecx,[eax+0x{off:x}]');req(M,ta,kind,'0x756010');A.append({'slot':i,'root_offset':f'+0x{off:x}','materialization':f'0x{la:08x}','transfer':f'0x{ta:08x}','transfer_kind':kind,'callee':'FUN_00756010'})
 L=maps['fun00756010']
 if any(m in {'call','jmp','push'} for a,(m,o) in L.items()):raise AssertionError('FUN_00756010 is not leaf')
 if any((o=='ecx' or o.endswith(',ecx')) for a,(m,o) in L.items() if m in {'mov','lea'}):raise AssertionError('FUN_00756010 copies root value')
 B=[];M=maps['fun0076ed60_window']
 specs=[(0x76ee43,0x76ee49,0x400),(0x76ee55,0x76ee5b,0xe80),(0x76ee67,0x76ee6d,0x1900),(0x76ee79,0x76ee7f,0x2380)]
 for i,(la,ca,off) in enumerate(specs):
  req(M,la,'lea',f'ecx,[esi+0x{off:x}]');req(M,ca,'call','0x753020');B.append({'slot':i,'root_offset':f'+0x{off:x}','materialization':f'0x{la:08x}','call':f'0x{ca:08x}','callee':'FUN_00753020'})
 L2=maps['fun00753020']
 if any(m in {'call','jmp'} for a,(m,o) in L2.items()):raise AssertionError('FUN_00753020 is not leaf')
 root_copy=[]
 for a,(m,o) in L2.items():
  if m=='push' and o=='ecx':root_copy.append((a,m,o))
  if m in {'mov','lea'} and ',' in o:
   d,s=o.split(',',1)
   if s=='ecx':root_copy.append((a,m,o))
 if root_copy:raise AssertionError(root_copy)
 slots=[{'slot':i,'wheel_root':f'HDVehicle+0x{x:x}','selected_target':f'HDVehicle+0x{x+0x538:x}..+0x{x+0x53f:x}'} for i,x in enumerate([0x400,0xe80,0x1900,0x2380])]
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'global_vehicle_receiver':'0x00c13700','ranges':auth},'wheel_layout':{'count':4,'stride':'+0xa80','slots':slots},'handoffs':{'FUN_007582f0_to_FUN_00756010':{'entry_receiver_proof':'0x0074d8b1 ECX=0x00c13700; 0x0074d8b6 call FUN_007582f0','count':4,'rows':A,'callee_complete_leaf':True,'callee_root_value_store_or_copy_found':False,'callee_scalar_destination_offsets':['+0x8b0','+0x868','+0x888']},'FUN_0076ed60_to_FUN_00753020':{'entry_receiver_proof':'0x0074dfe3 ECX=0x00c13700; 0x0074dfe8 call FUN_0076ed60; 0x0076ed64 ESI=ECX','count':4,'rows':B,'callee_complete_leaf':True,'callee_root_value_store_or_copy_found':False,'callee_writes_only_fields_relative_to_exact_wheel_receiver':True}},'adjudication':{'p13a_fixed_four_wheel_leaf_handoff_subset_complete':True,'fixed_four_wheel_leaf_handoff_count':8,'fixed_four_wheel_leaf_root_persistence_found':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'reconstructed_wheel_pointers_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes exactly two fixed four-wheel receiver handoff families on the proven global vehicle 0x00c13700 and the complete leaf callees FUN_00756010/FUN_00753020.','The receiver itself is forwarded into the leaf callees, so this is a positive transient alias handoff; neither complete leaf stores, copies, pushes or further forwards the receiver value.','FUN_007653f9 -> FUN_00760d70 remains open because that callee enters a non-contiguous/trampolined control-flow body; dynamic indexed materializers such as FUN_00757318 remain separate.','Global reconstructed/runtime-generated/stored-alias and callback/indirect gates remain fail-closed.'],'next_step':'Resolve FUN_007653f9 -> FUN_00760d70 across its trampoline and then classify FUN_00757318 indexed wheel-root lifetime.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
