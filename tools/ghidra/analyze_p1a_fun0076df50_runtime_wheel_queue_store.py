#!/usr/bin/env python3
"""Prove the FUN_0076df50 four-wheel runtime queue pointer-store/consumer path."""
from __future__ import annotations
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun0076df50RuntimeWheelQueueStore/1'
RETAIL_SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
WHEEL_VPTR=0x00b09a68
WHEEL_SLOT4_TARGET=0x0075cfb0
RANGES={
 'selected_hdvehicle_caller':(0x00798f97,0x00798fa1,'2134b802158e59b84e2c746abd12f6db1a4b875a93623808a19f0d538149c08d'),
 'fun0076df50_wheel_loop':(0x0076e4ac,0x0076e512,'7e1490ab82ff57f10d2e5b2499e8ca39bb43a5ececa8a2d346810366d2007c6f'),
 'fun00a62690_wheel_init':(0x00a62690,0x00a626c9,'da54e07d14af4c90f1c3defc4d2992a11c776f4f641c961cacbb779e144690b4'),
 'fun00a62c30_queue_node_alloc':(0x00a62c30,0x00a62ca5,'ae50955fea73d9f8c7805b0d0cffef4b90fca64f7dbddbef65fdb36a6237ba66'),
 'fun00a62f60_queue_register':(0x00a62f60,0x00a62fc8,'31d7c42ff25684a56fcb424f2cab1c91613b3387ef808c10cd7c0006daaab54e'),
 'wheel_constructor_vptr':(0x0076b098,0x0076b0a8,'b02199ed822256698ac54fae5bfdb4d9687b1c96a4f985cb1903f2b3e12b200d'),
 'wheel_vtable_slot01':(0x00b09a68,0x00b09a70,'a0a7ee6292a11c8c7e582fc654bda7bd4663b43b730a9e848ce8f8d6bb089dff'),
 'queue_execute_pack':(0x00a62a03,0x00a62a49,'d6f3db2b085fd4660c68f8f4b79c908bcb8029f293747dbbe532ebd542b3e474'),
 'fiber_virtual_dispatch':(0x00a62718,0x00a6272e,'1b663770eda4394194ef84e8f42de8ee9a52d548e83042be17e2bc5d293090c0'),
}
INST_RE=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')

def pe_sections(blob:bytes):
 pe=struct.unpack_from('<I',blob,0x3c)[0]; coff=pe+4
 nsec=struct.unpack_from('<H',blob,coff+2)[0]; optsz=struct.unpack_from('<H',blob,coff+16)[0]; opt=coff+20
 if struct.unpack_from('<H',blob,opt)[0] != 0x10b: raise ValueError('not PE32')
 imagebase=struct.unpack_from('<I',blob,opt+28)[0]; sh=opt+optsz; out=[]
 for i in range(nsec):
  o=sh+i*40; name=blob[o:o+8].rstrip(b'\0').decode('ascii','replace'); vs,va,rs,rp=struct.unpack_from('<IIII',blob,o+8)
  out.append((name,imagebase+va,max(vs,rs),rp))
 return out

def raw_va(blob:bytes,sections,s:int,e:int)->bytes:
 for _,va,span,rp in sections:
  if va <= s and e <= va+span:
   off=rp+(s-va); data=blob[off:off+(e-s)]
   if len(data)!=e-s: break
   return data
 raise ValueError(f'unmapped range {s:#x}..{e:#x}')

def dis(exe:Path,s:int,e:int):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out={}
 for line in p.stdout.splitlines():
  m=INST_RE.match(line)
  if m: out[int(m.group(1),16)]=(m.group(2).lower(),re.sub(r'\s+',' ',m.group(3).strip()).replace(', ',','))
 return out

def req(M,a,m,o):
 got=M.get(a); exp=(m,re.sub(r'\s+',' ',o.strip()).replace(', ',','))
 if got!=exp: raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {m} {exp[1]}'

def analyze(exe:Path):
 blob=exe.read_bytes(); sha=hashlib.sha256(blob).hexdigest()
 if sha!=RETAIL_SHA: raise ValueError(f'unexpected retail SHA256: {sha}')
 secs=pe_sections(blob); auth={}
 for name,(s,e,h) in RANGES.items():
  raw=raw_va(blob,secs,s,e); got=hashlib.sha256(raw).hexdigest()
  if got!=h: raise AssertionError(('range drift',name,got,h))
  auth[name]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 C=dis(exe,0x798f97,0x798fa1); L=dis(exe,0x76e4ac,0x76e512); I=dis(exe,0xa62690,0xa626c9)
 A=dis(exe,0xa62c30,0xa62ca5); R=dis(exe,0xa62f60,0xa62fc8); V=dis(exe,0x76b098,0x76b0a8)
 Q=dis(exe,0xa62a03,0xa62a49); F=dis(exe,0xa62718,0xa6272e)
 anchors={
  'selected_hdvehicle_literal':req(C,0x798f97,'mov','ecx,0xc13700'),
  'selected_hdvehicle_init_call':req(C,0x798f9c,'call','0x76df50'),
  'wheel_loop_counter_zero':req(L,0x76e4ac,'xor','edi,edi'),
  'wheel_slot0_materialization':req(L,0x76e4b4,'lea','ebx,[esi+0x400]'),
  'wheel_init_receiver':req(L,0x76e4f0,'mov','ecx,ebx'),
  'wheel_init_call':req(L,0x76e4f2,'call','0xa62690'),
  'wheel_queue_argument':req(L,0x76e4f7,'mov','edx,ebx'),
  'wheel_queue_manager':req(L,0x76e4f9,'lea','ecx,[esi+0x6730]'),
  'wheel_queue_register_call':req(L,0x76e4ff,'call','0xa62f60'),
  'wheel_stride':req(L,0x76e507,'add','ebx,0xa80'),
  'wheel_loop_bound':req(L,0x76e50d,'cmp','edi,0x4'),
  'wheel_loop_backedge':req(L,0x76e510,'jb','0x76e4e4'),
  'wheel_init_capture':req(I,0xa62694,'mov','esi,ecx'),
  'queue_node_allocator_call':req(R,0xa62f98,'call','0xa62c30'),
  'queue_node_capture':req(R,0xa62f9d,'mov','esi,eax'),
  'queue_task_pointer_store':req(R,0xa62fc0,'mov','DWORD PTR [esi],ebx'),
  'allocator_payload_call':req(A,0xa62c7b,'call','0x62f6f0'),
  'allocator_return_payload':req(A,0xa62c9e,'mov','eax,ebx'),
  'wheel_vptr_store':req(V,0x76b0a2,'mov','DWORD PTR [esi],0xb09a68'),
  'queue_record_task_load':req(Q,0xa62a06,'mov','eax,DWORD PTR [esi]'),
  'fiber_entry_pack':req(Q,0xa62a3d,'push','0xa62710'),
  'fiber_task_load':req(F,0xa6271b,'mov','esi,DWORD PTR [edi]'),
  'fiber_vptr_load':req(F,0xa62720,'mov','eax,DWORD PTR [esi]'),
  'fiber_slot4_load':req(F,0xa62722,'mov','eax,DWORD PTR [eax+0x4]'),
  'fiber_receiver_restore':req(F,0xa6272a,'mov','ecx,esi'),
  'fiber_virtual_call':req(F,0xa6272c,'call','eax'),
 }
 vt=raw_va(blob,secs,WHEEL_VPTR,WHEEL_VPTR+8); slot0,slot4=struct.unpack('<II',vt)
 if slot0!=0x0076b100 or slot4!=WHEEL_SLOT4_TARGET: raise AssertionError((hex(slot0),hex(slot4)))
 scalar_offsets=[]
 for _,(m,o) in I.items():
  mm=re.match(r'DWORD PTR \[esi\+0x([0-9a-f]+)\],',o) if m=='mov' else None
  if mm: scalar_offsets.append(int(mm.group(1),16))
 if scalar_offsets != [0x8,0x10,0x18,0x1c,0x20]: raise AssertionError(scalar_offsets)
 if any(m=='mov' and o.startswith('DWORD PTR [') and o.endswith(',esi') for m,o in I.values()): raise AssertionError('wheel init stores receiver')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'machine_bytes_adjudicate':True,'ranges':auth},
  'selected_hdvehicle_entry':{'caller_site':'0x00798f9c','receiver_literal':'0x00c13700','callee':'FUN_0076df50'},
  'four_wheel_loop':{'root_formula':'HDVehicle+0x400 + slot*0xa80','slot_count':4,'slots':[0,1,2,3],'roots':['HDVehicle+0x400','HDVehicle+0xe80','HDVehicle+0x1900','HDVehicle+0x2380'],'selected_slot_roots':{'slot0':'HDVehicle+0x400','slot1':'HDVehicle+0xe80'},'wheel_initializer':'FUN_00a62690','initializer_pointer_persistence_found':False,'queue_manager':'HDVehicle+0x6730','queue_register':'FUN_00a62f60'},
  'runtime_pointer_store':{'source':'exact wheel root in EDX -> EBX','runtime_node_allocator':'FUN_00a62c30 -> FUN_0062f6f0','runtime_node_register':'ESI','store_site':'0x00a62fc0','store':'[runtime_node+0x0] = exact wheel root','stores_per_fun0076df50_wheel_loop':4,'slot0_store_found':True,'slot1_store_found':True},
  'consumer_path':{'queue_execute':'FUN_00a62940','fiber_entry':'lpStartAddress_00a62710','runtime_node_task_pointer_reloaded':True,'consumer_receiver_is_exact_stored_wheel_root':True,'dispatch':'exact stored wheel root -> vptr -> slot +0x4 -> indirect call','wheel_constructor':'FUN_0076b060','wheel_vptr':f'0x{WHEEL_VPTR:08x}','wheel_vtable_slot_0':'0x0076b100','wheel_vtable_slot_4':f'0x{slot4:08x}','resolved_slot_4_target':f'0x{WHEEL_SLOT4_TARGET:08x}'},
  'machine_anchors':anchors,
  'adjudication':{'p13a_fun0076df50_runtime_wheel_queue_store_subset_complete':True,'runtime_generated_selected_wheel_pointer_store_found':True,'runtime_generated_selected_wheel_pointer_store_count_per_initialization':4,'slot0_runtime_wheel_pointer_store_found':True,'slot1_runtime_wheel_pointer_store_found':True,'stored_wheel_pointer_indirect_virtual_consumer_found':True,'stored_wheel_pointer_virtual_slot_4_target_resolved':True,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'reconstructed_wheel_pointers_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['This is a positive runtime pointer-persistence proof for the exact four-wheel loop in FUN_0076df50; it does not claim that every runtime-generated selected-wheel pointer store has been enumerated.','The queue manager at HDVehicle+0x6730 is a distinct non-wheel subobject, but its allocated node payload at +0 stores the exact wheel-root pointer.','The generic queue consumer reloads that stored pointer and invokes its virtual slot +0x4; the retail wheel vtable resolves that slot to 0x0075cfb0.','Because a selected-wheel pointer store is positively present, global runtime-generated-pointer, stored-alias, slot0/slot1 and aggregate P1.3 gates remain fail-closed.'],
  'next_step':'Trace 0x0075cfb0 wheel virtual-update semantics and enumerate any additional wheel-root registrations/stores outside FUN_0076df50; separately close residual indexed exact-root lifetimes in FUN_00765850/FUN_00765aa0.'
 }

def main():
 p=argparse.ArgumentParser();p.add_argument('executable',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();r=analyze(a.executable);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
