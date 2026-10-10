#!/usr/bin/env python3
"""Close the selected-wheel virtual slot +0x4 consumer reached by the runtime queue store."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13AWheelVirtualSlot4ConsumerClosure/1'
UPSTREAM_FORMAT='SHIFT.P1A.P13AFun0076df50RuntimeWheelQueueStore/1'
RETAIL_SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TARGET_START=0x0075CFB0
TARGET_END=0x00760B48
TARGET_SHA='16864e91b7b2af46fe7c18cd01209c37fbccbe6047633da6f70b26e3deb0f45d'
CALLEE_START=0x00755790
CALLEE_END=0x0075594A
CALLEE_SHA='33941107f8edbee236047ccc7e2d558ae3405e656cfecb389a792abcdc1d6117'
TEXT_VA=0x00401000; TEXT_RAW=0x400
TARGET_LO=0x538; TARGET_HI=0x540
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
MEM_ESI=re.compile(r'(?:(BYTE|WORD|DWORD|QWORD) PTR )?\[esi(?:\+0x([0-9a-fA-F]+))?\]')
SIZES={'BYTE':1,'WORD':2,'DWORD':4,'QWORD':8}
WRITE_MN={'mov','lea','xor','add','sub','and','or','imul','pop','movzx','movsx','inc','dec','shl','shr','sar','sal'}
REGS={'eax','ebx','ecx','edx','esi','edi'}

def norm(x):return re.sub(r'\s+',' ',x.strip()).replace(', ', ',')
def dis(exe,s,e):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out

def M(rows):return {a:(m,o) for a,m,o in rows}
def req(mp,a,m,o):
 exp=(m,norm(o));got=mp.get(a)
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {m} {exp[1]}'

def range_sha(blob,s,e):
 off=TEXT_RAW+(s-TEXT_VA); raw=blob[off:off+(e-s)]
 if len(raw)!=e-s:raise AssertionError((hex(s),len(raw),e-s))
 return hashlib.sha256(raw).hexdigest()

def target_overlap(rows):
 out=[]
 for a,m,o in rows:
  for mm in MEM_ESI.finditer(o):
   off=int(mm.group(2),16) if mm.group(2) else 0; size=SIZES.get(mm.group(1),1)
   if max(off,TARGET_LO)<min(off+size,TARGET_HI):
    out.append({'site':f'0x{a:08x}','mnemonic':m,'operands':o,'offset':f'+0x{off:x}','size':size})
 return out

def exact_root_surface(rows,capture_addr,pop_addrs):
 active=False; copies=[]; stores=[]; pushes=[]; writes=[]
 pop_addrs=set(pop_addrs)
 for a,m,o in rows:
  if a==capture_addr:active=True;continue
  if a in pop_addrs:continue
  if not active:continue
  if m=='push' and o=='esi':pushes.append(f'0x{a:08x}')
  if m=='mov' and o.endswith(',esi'):
   dst=o.split(',',1)[0]
   if dst in REGS:copies.append({'site':f'0x{a:08x}','dst':dst})
   elif dst.startswith(('BYTE PTR [','WORD PTR [','DWORD PTR [','QWORD PTR [')):stores.append({'site':f'0x{a:08x}','dst':dst})
  if m in WRITE_MN:
   dst=o.split(',',1)[0]
   if dst=='esi':writes.append({'site':f'0x{a:08x}','mnemonic':m,'operands':o})
 return {'register_copies':copies,'nonstack_pointer_stores':stores,'pushes':pushes,'writes_to_root_register':writes}

def analyze(exe:Path,upstream:Path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=RETAIL_SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM_FORMAT or up.get('ready') is not True:raise ValueError('unexpected upstream queue-store evidence')
 if up.get('authority',{}).get('retail_executable_sha256')!=sha:raise ValueError('upstream retail hash drift')
 ua=up.get('adjudication',{})
 if ua.get('runtime_generated_selected_wheel_pointer_store_found') is not True or ua.get('stored_wheel_pointer_virtual_slot_4_target_resolved') is not True:raise ValueError('upstream positive queue premise missing')
 if up.get('consumer_path',{}).get('resolved_slot_4_target')!='0x0075cfb0':raise ValueError('upstream slot +0x4 target drift')
 if range_sha(blob,TARGET_START,TARGET_END)!=TARGET_SHA:raise AssertionError('slot4 target range drift')
 if range_sha(blob,CALLEE_START,CALLEE_END)!=CALLEE_SHA:raise AssertionError('FUN_00755790 range drift')
 tr=dis(exe,TARGET_START,TARGET_END); cr=dis(exe,CALLEE_START,CALLEE_END); tm=M(tr);cm=M(cr)
 anchors={
  'target_receiver_capture':req(tm,0x75cfe5,'mov','esi,ecx'),
  'target_early_scalar_write':req(tm,0x75d001,'fst','QWORD PTR [esi+0x738]'),
  'target_exact_root_forward':req(tm,0x7606f4,'mov','ecx,esi'),
  'target_forward_call':req(tm,0x760705,'call','0x755790'),
  'target_return':req(tm,0x760b45,'ret','0x8'),
  'callee_receiver_capture':req(cm,0x7557b6,'mov','esi,ecx'),
  'callee_scalar_write_4b8':req(cm,0x7558e0,'fstp','QWORD PTR [esi+0x4b8]'),
  'callee_scalar_write_4c0':req(cm,0x7558e9,'fstp','QWORD PTR [esi+0x4c0]'),
  'callee_scalar_write_4c8':req(cm,0x7558f2,'fstp','QWORD PTR [esi+0x4c8]'),
  'callee_scalar_write_500':req(cm,0x755900,'fstp','DWORD PTR [esi+0x500]'),
  'callee_return_a':req(cm,0x75590e,'ret','0xc'),
  'callee_return_b':req(cm,0x755947,'ret','0xc'),
 }
 ts=exact_root_surface(tr,0x75cfe5,{0x760b3e});cs=exact_root_surface(cr,0x7557b6,{0x755907,0x755940})
 if ts['register_copies'] != [{'site':'0x007606f4','dst':'ecx'}]:raise AssertionError(('target copies',ts))
 if ts['nonstack_pointer_stores'] or ts['pushes'] or ts['writes_to_root_register']:raise AssertionError(('target root escape',ts))
 if cs['register_copies'] or cs['nonstack_pointer_stores'] or cs['pushes'] or cs['writes_to_root_register']:raise AssertionError(('callee root escape',cs))
 to=target_overlap(tr);co=target_overlap(cr)
 if to or co:raise AssertionError(('selected-target overlap',to,co))
 calls_after=[(a,m,o) for a,m,o in tr if 0x7606f4<a<=0x760705 and m=='call']
 if calls_after != [(0x760705,'call','0x755790')]:raise AssertionError(('forward call shape',calls_after))
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM_FORMAT,'machine_bytes_adjudicate':True,'ranges':{
   'wheel_virtual_slot4_target':{'start':'0x0075cfb0','end_exclusive':'0x00760b48','size':TARGET_END-TARGET_START,'sha256':TARGET_SHA},
   'FUN_00755790':{'start':'0x00755790','end_exclusive':'0x0075594a','size':CALLEE_END-CALLEE_START,'sha256':CALLEE_SHA},
  }},
  'selected_target':{'wheel_relative_range':'+0x538..+0x53f','slot0_absolute':'HDVehicle+0x938..+0x93f','slot1_absolute':'HDVehicle+0x13b8..+0x13bf'},
  'virtual_consumer':{'target':'0x0075cfb0','receiver':'exact persisted wheel root from runtime queue node','instruction_count':len(tr),'direct_selected_target_overlap_count':0,'direct_selected_target_overlaps':to,'exact_root_surface':ts,'exact_root_forward_count':1,'exact_root_forward':{'prep':'0x007606f4','call':'0x00760705','callee':'FUN_00755790'}},
  'forward_callee':{'function':'FUN_00755790','range_size':CALLEE_END-CALLEE_START,'direct_selected_target_overlap_count':0,'direct_selected_target_overlaps':co,'exact_root_surface':cs,'pointer_persistence_found':False,'selected_target_write_found':False},
  'machine_anchors':anchors,
  'adjudication':{
   'p13a_persisted_wheel_virtual_slot4_consumer_subset_complete':True,
   'persisted_wheel_virtual_slot4_selected_target_write_found':False,
   'persisted_wheel_virtual_slot4_exact_root_pointer_persistence_found':False,
   'persisted_wheel_virtual_slot4_only_exact_root_forward_closed':True,
   'runtime_generated_selected_wheel_pointer_store_found':True,
   'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
   'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
   'This closes the selected-wheel consumer reached through the proven FUN_0076df50 runtime queue node and retail wheel vtable +0x4 only; it does not enumerate other queue registrations or virtual slots.',
   'The 0x0075cfb0 target contains no wheel-relative memory access overlapping +0x538..+0x53f and no exact-root pointer store/push. Its sole exact-root forward is ECX=ESI into FUN_00755790.',
   'The complete pinned FUN_00755790 range likewise has no +0x538..+0x53f overlap and performs scalar root-relative updates without persisting or forwarding the exact root pointer.',
   'The positive queue pointer store from the upstream contract remains present, so global runtime-generated/stored-alias and slot/P1.3 gates remain fail-closed.'
  ],
  'next_step':'Enumerate other FUN_00a62f60 registrations whose source is an exact wheel root or selected-wheel-derived alias; compose them with residual indexed lifetimes before any global stored-alias decision.'
 }

def main():
 p=argparse.ArgumentParser();p.add_argument('executable',type=Path);p.add_argument('--upstream',type=Path,default=Path('evidence/p1a_p13a_fun0076df50_runtime_wheel_queue_store.json'));p.add_argument('--output',type=Path);a=p.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
