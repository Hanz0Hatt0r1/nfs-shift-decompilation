#!/usr/bin/env python3
"""Inventory direct FUN_00a62f60 registrations and isolate the one unresolved callback-source frontier."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AQueueRegistrationFrontier/1'
QUEUE_FORMAT='SHIFT.P1A.P13AFun0076df50RuntimeWheelQueueStore/1'
TASK_FORMAT='SHIFT.Process1Fun0079b2d0VirtualDispatch/1'
RETAIL_SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
QUEUE_REGISTER=0x00A62F60
CALLBACK=0x0067B660
CALLBACK_RANGE=(0x0067B660,0x0067B720,'58bb8b26934ed847ac33567b21cbf58d1c333e75867687228e79b104d3e942f7')
CALLBACK_TABLE_RANGE=(0x00AF7524,0x00AF7550,'583c47739d952aaac4938b60e2d823aa535bab374342b68c57772e2e4a953918')
DIRECT_SITES=[0x0067B69E,0x00713122,0x007131CC,0x0076E4FF]
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
DIRECT=re.compile(r'^0x([0-9a-fA-F]+)$')

def norm(x):return re.sub(r'\s+',' ',x.strip()).replace(', ', ',')
def pe_sections(b):
 pe=struct.unpack_from('<I',b,0x3c)[0];co=pe+4;n=struct.unpack_from('<H',b,co+2)[0];os=struct.unpack_from('<H',b,co+16)[0];op=co+20;ib=struct.unpack_from('<I',b,op+28)[0];sh=op+os;out=[]
 for i in range(n):
  o=sh+i*40;name=b[o:o+8].rstrip(b'\0').decode('ascii','replace');vs,va,rs,rp=struct.unpack_from('<IIII',b,o+8);out.append((name,ib+va,max(vs,rs),rp,rs))
 return out

def raw_va(b,secs,s,e):
 for name,va,span,rp,rs in secs:
  if va<=s and e<=va+span:
   raw=b[rp+s-va:rp+e-va]
   if len(raw)==e-s:return raw
 raise ValueError((hex(s),hex(e)))
def va_for_raw(secs,off):
 for name,va,span,rp,rs in secs:
  if rp<=off<rp+rs:return name,va+(off-rp)
 return None,None

def dis_rows(exe):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout
 out=[]
 for line in p.stdout:
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 err=p.stderr.read() if p.stderr else '';rc=p.wait()
 if rc:raise RuntimeError(err)
 return out

def region(exe,s,e):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True);out={}
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out[int(m.group(1),16)]=(m.group(2).lower(),norm(m.group(3)))
 return out

def req(mp,a,m,o):
 exp=(m,norm(o));got=mp.get(a)
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {m} {exp[1]}'

def analyze(exe:Path,queue_evidence:Path,task_evidence:Path):
 b=exe.read_bytes();sha=hashlib.sha256(b).hexdigest()
 if sha!=RETAIL_SHA:raise ValueError(sha)
 q=json.loads(queue_evidence.read_text(encoding='utf-8'));t=json.loads(task_evidence.read_text(encoding='utf-8'))
 if q.get('format')!=QUEUE_FORMAT or q.get('ready') is not True:raise ValueError('queue evidence format')
 if q.get('authority',{}).get('retail_executable_sha256')!=sha:raise ValueError('queue evidence hash')
 if q.get('runtime_pointer_store',{}).get('store_site')!='0x00a62fc0':raise ValueError('queue store drift')
 if t.get('format')!=TASK_FORMAT or t.get('ready') is not True:raise ValueError('task evidence format')
 if t.get('source',{}).get('retail_executable_sha256')!=sha:raise ValueError('task evidence hash')
 if t.get('queue_dispatch',{}).get('queue_register')!='FUN_00a62f60':raise ValueError('task queue register drift')
 if t.get('promotion',{}).get('subobject_identity_continuity_proven') is not True or t.get('promotion',{}).get('queue_registration_continuity_proven') is not True:raise ValueError('task continuity premise missing')
 rows=dis_rows(exe);sites=[];callback_direct=[]
 for a,m,o in rows:
  if m not in ('call','jmp'):continue
  dm=DIRECT.match(o)
  if not dm:continue
  target=int(dm.group(1),16)
  if m=='call' and target==QUEUE_REGISTER:sites.append(a)
  if target==CALLBACK:callback_direct.append({'site':f'0x{a:08x}','kind':m})
 if sites!=DIRECT_SITES:raise AssertionError(('direct queue surface',sites))
 if callback_direct:raise AssertionError(('callback direct transfer drift',callback_direct))
 secs=pe_sections(b)
 s,e,h=CALLBACK_RANGE
 if hashlib.sha256(raw_va(b,secs,s,e)).hexdigest()!=h:raise AssertionError('callback range drift')
 s2,e2,h2=CALLBACK_TABLE_RANGE
 if hashlib.sha256(raw_va(b,secs,s2,e2)).hexdigest()!=h2:raise AssertionError('callback table drift')
 pat=struct.pack('<I',CALLBACK);occ=[];pos=0
 while True:
  pos=b.find(pat,pos)
  if pos<0:break
  sec,va=va_for_raw(secs,pos);occ.append({'file_offset':f'0x{pos:08x}','section':sec,'va':f'0x{va:08x}' if va is not None else None});pos+=1
 if occ!=[{'file_offset':'0x006f5f48','section':'.rdata','va':'0x00af7548'}]:raise AssertionError(('callback pointer occurrences',occ))
 C=region(exe,0x67b660,0x67b6b1);P=region(exe,0x713117,0x7131d1);W=region(exe,0x76e4f7,0x76e504)
 anchors={
  'callback_param_capture':req(C,0x67b667,'mov','esi,DWORD PTR [ebp+0x8]'),
  'callback_source_base':req(C,0x67b67c,'lea','edi,[esi+0x130]'),
  'callback_source_arg':req(C,0x67b696,'mov','edx,edi'),
  'callback_queue_manager':req(C,0x67b698,'lea','ecx,[esi+0x2b0]'),
  'callback_queue_call':req(C,0x67b69e,'call','0xa62f60'),
  'callback_source_stride':req(C,0x67b6a6,'add','edi,0x30'),
  'task_selected_source':req(P,0x713117,'mov','edx,DWORD PTR [ebx]'),
  'task_selected_subobject':req(P,0x713119,'add','edx,0x340'),
  'task_selected_queue_call':req(P,0x713122,'call','0xa62f60'),
  'task_loop_source':req(P,0x7131ba,'mov','edx,DWORD PTR [esi+0x140]'),
  'task_loop_element':req(P,0x7131c0,'mov','edx,DWORD PTR [edx+edi*1]'),
  'task_loop_subobject':req(P,0x7131c3,'add','edx,0x340'),
  'task_loop_queue_call':req(P,0x7131cc,'call','0xa62f60'),
  'wheel_source':req(W,0x76e4f7,'mov','edx,ebx'),
  'wheel_queue_manager':req(W,0x76e4f9,'lea','ecx,[esi+0x6730]'),
  'wheel_queue_call':req(W,0x76e4ff,'call','0xa62f60'),
 }
 spans=t['queue_dispatch']['machine_spans']
 if spans['register_selected_subobject']['start']!='0x00713117' or spans['register_selected_subobject']['end_exclusive']!='0x00713127':raise ValueError('selected task span drift')
 if spans['register_loop_subobject']['start']!='0x007131ba' or spans['register_loop_subobject']['end_exclusive']!='0x007131d1':raise ValueError('loop task span drift')
 if t['object_provenance'].get('subobject_offset')!='0x340':raise ValueError('task subobject offset drift')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'machine_disassembly_adjudicates_direct_calls':True,'upstream_contracts':[QUEUE_FORMAT,TASK_FORMAT],
   'callback_range':{'start':'0x0067b660','end_exclusive':'0x0067b720','size':192,'sha256':CALLBACK_RANGE[2]},
   'callback_table_range':{'start':'0x00af7524','end_exclusive':'0x00af7550','size':44,'sha256':CALLBACK_TABLE_RANGE[2]}},
  'direct_registration_surface':{'target':'FUN_00a62f60','count':4,'callsites':[f'0x{x:08x}' for x in sites],
   'classifications':[
    {'site':'0x0067b69e','owner':'FUN_0067b660','source':'param_1+0x130 + index*0x30','queue_manager':'param_1+0x2b0','class':'unresolved-callback-source','selected_wheel_root_proven':False,'selected_wheel_root_ruled_out':False},
    {'site':'0x00713122','owner':'FUN_00713050','source':'parent->subobject(+0x340)','class':'proven-distinct-task-subobject','selected_wheel_root_proven':False,'selected_wheel_root_ruled_out':True},
    {'site':'0x007131cc','owner':'FUN_00713050','source':'loop parent->subobject(+0x340)','class':'proven-distinct-task-subobject','selected_wheel_root_proven':False,'selected_wheel_root_ruled_out':True},
    {'site':'0x0076e4ff','owner':'FUN_0076df50','source':'exact wheel root HDVehicle+0x400+slot*0xa80','class':'proven-selected-wheel-root','selected_wheel_root_proven':True,'selected_wheel_root_ruled_out':False},
   ],'proven_selected_wheel_registration_count':1,'proven_nonwheel_registration_count':2,'unresolved_source_registration_count':1},
  'callback_frontier':{'function':'FUN_0067b660','direct_transfer_count':0,'absolute_pointer_occurrence_count':1,'absolute_pointer_occurrences':occ,'static_table_pointer_va':'0x00af7548','adjacent_static_string':'AnimationProcessor::mStartEvent','argument_source_formula':'param_1+0x130 + index*0x30','argument_stride':'0x30','argument_provenance_complete':False},
  'machine_anchors':anchors,
  'adjudication':{'p13a_fun00a62f60_direct_registration_surface_complete':True,'fun00a62f60_direct_registration_count':4,'fun00a62f60_proven_selected_wheel_registration_count':1,'fun00a62f60_proven_nonwheel_registration_count':2,'fun00a62f60_unresolved_source_registration_count':1,'fun0067b660_static_callback_pointer_found':True,'fun0067b660_callback_argument_provenance_complete':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['The whole-image direct-call surface to FUN_00a62f60 is exact: four callsites. One is the proven four-wheel registration from FUN_0076df50 and two are independently proven +0x340 task subobjects from FUN_00713050.','FUN_0067b660 supplies the fourth source as param_1+0x130 with 0x30 stride. It has no direct call/jump entry but its address occurs once in .rdata at 0x00af7548 next to the AnimationProcessor::mStartEvent static table.','This contract deliberately leaves FUN_0067b660 callback argument provenance open; the source cannot be declared non-wheel until the table invocation/argument ABI is recovered.','Indirect calls to FUN_00a62f60 or runtime-written registration targets are outside this direct-call inventory. Global callback, runtime-generated-pointer, stored-alias and slot/P1.3 gates remain fail-closed.'],
  'next_step':'Recover the static callback table invocation that reaches FUN_0067b660 and prove the param_1 object identity/argument ABI; then the full direct FUN_00a62f60 registration source surface can be classified.'
 }

def main():
 p=argparse.ArgumentParser();p.add_argument('executable',type=Path);p.add_argument('--queue-evidence',type=Path,default=Path('evidence/p1a_p13a_fun0076df50_runtime_wheel_queue_store.json'));p.add_argument('--task-evidence',type=Path,default=Path('evidence/process1_fun_0079b2d0_virtual_dispatch.json'));p.add_argument('--output',type=Path);a=p.parse_args();r=analyze(a.executable,a.queue_evidence,a.task_evidence);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
