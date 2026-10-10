#!/usr/bin/env python3
"""Pin the FUN_0067b660 static vtable object and embedded queue-source layout."""
from __future__ import annotations
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun0067b660StaticVtableObject/1'
UPSTREAM_FORMAT='SHIFT.P1A.P13AQueueRegistrationFrontier/1'
RETAIL_SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
CTOR=0x0067B7B0
VTABLE=0x00AF7544
SOURCE_VTABLE=0x00AF74F4
RANGES={
 'constructor':(0x0067b7b0,0x0067b849,'d592315b9df2a6c6b49723b87c26095436f8b19faa590a31b1ebba7ee34d8ef4'),
 'destructor':(0x0067b850,0x0067b8bc,'59690907327bdaf8336880ceb03ce9354323da4ae91bc625fe7d58c939ef1857'),
 'callback_body':(0x0067b660,0x0067b720,'58bb8b26934ed847ac33567b21cbf58d1c333e75867687228e79b104d3e942f7'),
 'object_vtable':(0x00af7544,0x00af7550,'05cf68ee84264357361e9d7956aa279eda83851a024e29d58f806b8675545b37'),
 'source_record_vtable':(0x00af74f4,0x00af74fc,'f93268918771209fe4428fbc9826136cfdb11477e1b4776580be96ec5925afb8'),
 'caller_parent_plus_8a0':(0x00489166,0x00489176,'db85d347cde63d7a05264a567fb1db27757e4c77c68303682036cf166e92d7ce'),
 'caller_parent_plus_2c0':(0x0067b160,0x0067b185,'551c4b69ad0bcc9253c9a8be50e59c2fca10a15e215b256da8784c597809dddd'),
 'caller_parent_plus_320':(0x00d4b52e,0x00d4b553,'9898fa6904e192ab669f7d350872ddc335c079240150baca15e4d9042df9832c'),
}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
DIRECT=re.compile(r'^0x([0-9a-fA-F]+)$')

def norm(x):return re.sub(r'\s+',' ',x.strip()).replace(', ', ',')
def pe_sections(b):
 pe=struct.unpack_from('<I',b,0x3c)[0];co=pe+4;n=struct.unpack_from('<H',b,co+2)[0];os=struct.unpack_from('<H',b,co+16)[0];op=co+20
 if struct.unpack_from('<H',b,op)[0]!=0x10b:raise ValueError('not PE32')
 ib=struct.unpack_from('<I',b,op+28)[0];sh=op+os;out=[]
 for i in range(n):
  o=sh+i*40;name=b[o:o+8].rstrip(b'\0').decode('ascii','replace');vs,va,rs,rp=struct.unpack_from('<IIII',b,o+8);out.append((name,ib+va,max(vs,rs),rp,rs))
 return out

def raw_va(b,secs,s,e):
 for name,va,span,rp,rs in secs:
  if va<=s and e<=va+span:
   x=b[rp+s-va:rp+e-va]
   if len(x)==e-s:return x
 raise ValueError((hex(s),hex(e)))
def dis(exe,s,e):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True);out={}
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out[int(m.group(1),16)]=(m.group(2).lower(),norm(m.group(3)))
 return out

def all_direct_calls(exe,target):
 p=subprocess.Popen(['objdump','-d','-Mintel',str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,errors='replace');assert p.stdout
 out=[]
 for line in p.stdout:
  m=I.match(line)
  if not m or m.group(2).lower()!='call':continue
  dm=DIRECT.match(norm(m.group(3)))
  if dm and int(dm.group(1),16)==target:out.append(int(m.group(1),16))
 err=p.stderr.read() if p.stderr else '';rc=p.wait()
 if rc:raise RuntimeError(err)
 return out

def req(mp,a,m,o):
 exp=(m,norm(o));got=mp.get(a)
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {m} {exp[1]}'
def dwords(raw):return list(struct.unpack('<'+'I'*(len(raw)//4),raw))

def analyze(exe:Path,upstream:Path):
 b=exe.read_bytes();sha=hashlib.sha256(b).hexdigest()
 if sha!=RETAIL_SHA:raise ValueError(sha)
 up=json.loads(upstream.read_text(encoding='utf-8'))
 if up.get('format')!=UPSTREAM_FORMAT or up.get('ready') is not True:raise ValueError('upstream queue frontier')
 if up.get('authority',{}).get('retail_executable_sha256')!=sha:raise ValueError('upstream hash drift')
 if up.get('callback_frontier',{}).get('function')!='FUN_0067b660' or up.get('callback_frontier',{}).get('static_table_pointer_va')!='0x00af7548':raise ValueError('callback frontier drift')
 secs=pe_sections(b);auth={}
 for n,(s,e,h) in RANGES.items():
  raw=raw_va(b,secs,s,e);g=hashlib.sha256(raw).hexdigest()
  if g!=h:raise AssertionError(('range drift',n,g,h))
  auth[n]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 vt=dwords(raw_va(b,secs,VTABLE,VTABLE+12));svt=dwords(raw_va(b,secs,SOURCE_VTABLE,SOURCE_VTABLE+8))
 if vt != [0x0067b8c0,0x0067b660,0x0067b330]:raise AssertionError(('vtable',vt))
 if svt != [0x0067b300,0x0067b730]:raise AssertionError(('source vtable',svt))
 calls=all_direct_calls(exe,CTOR)
 if calls != [0x00489171,0x0067b180,0x00d4b54e]:raise AssertionError(('ctor calls',calls))
 C=dis(exe,0x67b7b0,0x67b849);D=dis(exe,0x67b850,0x67b8bc);A=dis(exe,0x489166,0x489176);B=dis(exe,0x67b160,0x67b185);S=dis(exe,0xd4b52e,0xd4b553)
 anchors={
  'ctor_vptr_store':req(C,0x67b7c5,'mov','DWORD PTR [esi],0xaf7544'),
  'ctor_source_base':req(C,0x67b81a,'lea','edi,[esi+0x130]'),
  'ctor_source_loop_count_seed':req(C,0x67b7f5,'mov','eax,0x10'),
  'ctor_source_loop_count_derive':req(C,0x67b820,'lea','ebx,[eax-0x9]'),
  'ctor_source_construct':req(C,0x67b825,'call','0xa62620'),
  'ctor_source_vptr_store':req(C,0x67b82a,'mov','DWORD PTR [edi],0xaf74f4'),
  'ctor_source_stride':req(C,0x67b830,'add','edi,0x30'),
  'ctor_source_loop_dec':req(C,0x67b833,'sub','ebx,0x1'),
  'ctor_source_loop_backedge':req(C,0x67b836,'jns','0x67b823'),
  'ctor_queue_base':req(C,0x67b838,'lea','ecx,[esi+0x2b0]'),
  'ctor_queue_init':req(C,0x67b83e,'call','0xa62cb0'),
  'dtor_vptr_restore':req(D,0x67b85b,'mov','DWORD PTR [esi],0xaf7544'),
  'dtor_queue_base':req(D,0x67b855,'lea','ecx,[esi+0x2b0]'),
  'dtor_queue_destroy':req(D,0x67b861,'call','0xa62d40'),
  'caller_8a0_receiver':req(A,0x48916b,'lea','ecx,[esi+0x8a0]'),
  'caller_8a0_call':req(A,0x489171,'call','0x67b7b0'),
  'caller_2c0_receiver':req(B,0x67b165,'lea','ecx,[esi+0x2c0]'),
  'caller_2c0_call':req(B,0x67b180,'call','0x67b7b0'),
  'caller_320_receiver':req(S,0xd4b533,'lea','ecx,[ebx+0x320]'),
  'caller_320_call':req(S,0xd4b54e,'call','0x67b7b0'),
 }
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM_FORMAT,'machine_bytes_adjudicate':True,'ranges':auth},
  'object_vtable':{'address':'0x00af7544','entries':[{'slot':'+0x0','target':'0x0067b8c0','role':'destructor-like'},{'slot':'+0x4','target':'0x0067b660','role':'queue-registration callback frontier'},{'slot':'+0x8','target':'0x0067b330','role':'state method'}],'fun0067b660_is_exact_slot_4':True},
  'constructor_layout':{'constructor':'FUN_0067b7b0','direct_call_count':3,'direct_calls':[f'0x{x:08x}' for x in calls],'embedded_instance_offsets':['parent+0x8a0','parent+0x2c0','parent+0x320'],'source_record_base':'+0x130','source_record_stride':'0x30','source_record_count':7,'source_record_vtable':'0x00af74f4','source_record_vtable_entries':['0x0067b300','0x0067b730'],'queue_manager_offset':'+0x2b0'},
  'callback_argument_boundary':{'slot4_target':'FUN_0067b660','ghidra_stack_argument':'param_1 at [EBP+0x8]','slot4_method_uses_ecx_receiver':False,'param1_equals_vtable_object_this_proven':False,'param1_object_identity_complete':False,'note':'The constructor proves the class layout, but not what explicit stack argument the indirect slot +0x4 dispatcher supplies.'},
  'machine_anchors':anchors,
  'adjudication':{'p13a_fun0067b660_static_vtable_object_identity_complete':True,'fun0067b660_exact_vtable_slot_4_proven':True,'fun0067b660_constructor_layout_complete':True,'fun0067b660_source_record_layout_complete':True,'fun0067b660_callback_argument_provenance_complete':False,'fun0067b660_callback_argument_is_selected_wheel_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['This proves that 0x0067b660 is exactly vtable slot +0x4 of the class constructed by FUN_0067b7b0 and pins that class layout.','The constructor creates exactly seven embedded source records starting at this+0x130 with stride 0x30, installs source-record vptr 0x00af74f4, and initializes the queue manager at this+0x2b0.','FUN_0067b7b0 has exactly three direct construction sites, embedding instances at parent+0x8a0, parent+0x2c0 and parent+0x320.','The slot +0x4 method ignores ECX and consumes an explicit stack param_1. This contract does not assume param_1 equals the vtable object receiver; its dispatcher/argument provenance remains open.'],
  'next_step':'Recover indirect dispatch to vtable 0x00af7544 slot +0x4 and prove the explicit stack param_1 identity. Only then classify the remaining direct FUN_00a62f60 source at 0x0067b69e.'
 }

def main():
 p=argparse.ArgumentParser();p.add_argument('executable',type=Path);p.add_argument('--upstream',type=Path,default=Path('evidence/p1a_p13a_queue_registration_frontier.json'));p.add_argument('--output',type=Path);a=p.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
