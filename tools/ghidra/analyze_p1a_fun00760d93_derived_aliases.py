#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun00760d93DerivedAliasClosure/1'
UPSTREAM='SHIFT.P1A.P13ATrampolinedWheelRootLifetime/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TEXT_VA=0x401000;TEXT_RAW=0x400
RANGES={
 'fun00760d93':(0x760d93,0x760f79,'c5dc2f0564fcefd31dab2555f7fa910758739cc9e95a1ac8029f995ea6d088f1'),
 'fun007538a0':(0x7538a0,0x75391e,'780fd2c2b532fa18db0c02dc010f4f36d090ae611a0dffb44ee4346f424478c4'),
 'fun007ba630':(0x7ba630,0x7ba7de,'4d7c11507756faf8213747d354ff9ab30ec1162693286afb69de241718f9080c'),
 'fun007ba7e0':(0x7ba7e0,0x7ba852,'c44dac55776ac266f00822c40762b2d452226a043a0bd687209b67d3bbe947a4'),
 'fun007b1790':(0x7b1790,0x7b19e9,'44969e5c54b61563c235d2c6fad3da9e062d1184920e30b48c4219552cf23359'),
 'fun00753710':(0x753710,0x75375c,'5fbab5956392a1d73e81f20090b28894631d0a9b0f7e130e4c3d6d4401fe0ea0'),
}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe,s,e):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for l in p.stdout.splitlines():
  m=I.match(l)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def req(M,a,m,o=''):
 got=M.get(a);exp=(m,norm(o))
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {m} {exp[1]}'.rstrip()
def no_bare_value_escape(rows,reg,start=0):
 bad=[]
 for a,m,o in rows:
  if a<start:continue
  if m=='push' and o==reg:bad.append((a,m,o))
  if m in {'mov','lea'} and ',' in o:
   d,s=o.split(',',1)
   if s==reg and not (d in {'esi','edi'} and a==start):bad.append((a,m,o))
  if m=='xchg' and reg in o.split(','):bad.append((a,m,o))
 return bad
def analyze(exe:Path,upstream:Path):
 b=exe.read_bytes();sha=hashlib.sha256(b).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 u=json.loads(upstream.read_text())
 if u['format']!=UPSTREAM or not u['adjudication']['p13a_trampolined_wheel_root_exact_lifetime_subset_complete']:raise AssertionError('upstream')
 auth={};maps={};rows={}
 for n,(s,e,h) in RANGES.items():
  raw=b[TEXT_RAW+s-TEXT_VA:TEXT_RAW+e-TEXT_VA]
  if len(raw)!=e-s or hashlib.sha256(raw).hexdigest()!=h:raise AssertionError(('range',n))
  rr=dis(exe,s,e);rows[n]=rr;maps[n]={a:(m,o) for a,m,o in rr};auth[n]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 M=maps['fun00760d93'];A={}
 A['child420_first']=req(M,0x760dbc,'mov','eax,DWORD PTR [esi+0x420]');A['child420_callprep']=req(M,0x760de4,'mov','ecx,DWORD PTR [esi+0x420]');A['child420_call']=req(M,0x760dea,'call','0x7538a0')
 A['child424_first']=req(M,0x760dfc,'mov','eax,DWORD PTR [esi+0x424]');A['child424_callprep']=req(M,0x760e26,'mov','ecx,DWORD PTR [esi+0x424]');A['child424_call']=req(M,0x760e2c,'call','0x7538a0')
 A['interior508']=req(M,0x760ea3,'lea','edx,[esi+0x508]');A['interior508_push']=req(M,0x760ea9,'push','edx');A['interior508_call']=req(M,0x760ead,'call','0x7b1790')
 A['interior9b0']=req(M,0x760f22,'lea','ecx,[esi+0x9b0]');A['interior9b0_call']=req(M,0x760f2b,'call','0x753710')
 C=maps['fun007538a0'];req(C,0x7538a9,'mov','esi,ecx');req(C,0x7538f9,'call','0x7ba630');req(C,0x753903,'mov','ecx,esi');req(C,0x753914,'call','0x7ba7e0')
 bad7538=no_bare_value_escape(rows['fun007538a0'],'esi',0x7538a9)
 if bad7538!=[(0x753903,'mov','ecx,esi')]:raise AssertionError(('7538a0 child forwarding',bad7538))
 if any(m in {'call','jmp'} for _,m,_ in rows['fun007ba630']):raise AssertionError('7ba630 not leaf')
 bad630=no_bare_value_escape(rows['fun007ba630'],'ecx')
 if bad630:raise AssertionError(('7ba630 child escape',bad630))
 C2=maps['fun007ba7e0'];req(C2,0x7ba7fb,'mov','esi,ecx');req(C2,0x7ba801,'lea','ecx,[esi+0x18]');req(C2,0x7ba804,'lea','edi,[esi+0xd4]');req(C2,0x7ba80d,'call','0x7af0a0');req(C2,0x7ba81e,'add','esi,0x30');req(C2,0x7ba835,'mov','ecx,edi');req(C2,0x7ba844,'call','0x7aefb0')
 # after capture, raw child ESI is never stored/pushed/copied; only interior aliases are derived.
 bad7e0=[]
 for a,m,o in rows['fun007ba7e0']:
  if a<=0x7ba7fb:continue
  if m=='push' and o=='esi' and a<0x7ba81e:bad7e0.append((a,m,o))
  if m in {'mov','lea'} and ',' in o:
   d,s=o.split(',',1)
   if s=='esi':bad7e0.append((a,m,o))
 if bad7e0:raise AssertionError(('7ba7e0 raw child escape',bad7e0))
 V=maps['fun007b1790'];req(V,0x7b17ae,'mov','edi,DWORD PTR [ebx+0x8]');req(V,0x7b19d7,'mov','ecx,esi');req(V,0x7b19d9,'call','0x75c0d0')
 bad508=[]
 for a,m,o in rows['fun007b1790']:
  if a<=0x7b17ae:continue
  if m=='push' and o=='edi':bad508.append((a,m,o))
  if m in {'mov','lea'} and ',' in o and o.split(',',1)[1]=='edi':bad508.append((a,m,o))
 if bad508:raise AssertionError(('508 persistence',bad508))
 Q=maps['fun00753710'];req(Q,0x75371a,'mov','esi,ecx');req(Q,0x753759,'ret','0x8')
 bad9=no_bare_value_escape(rows['fun00753710'],'esi',0x75371a)
 if bad9:raise AssertionError(('9b0 persistence',bad9))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM,'ranges':auth},'aliases':{
  'wheel_420_child':{'source':'[wheel+0x420]','caller':'FUN_00760d93','callee':'FUN_007538a0','callee_scalar_writes':['child+0xd4..+0xf4','child+0x18/+0x20/+0x28'],'transitive_exact_child_call':'FUN_007ba630','transitive_derived_child_call':'FUN_007ba7e0','exact_child_persistence_found':False,'wheel_root_reconstruction_found':False},
  'wheel_424_child':{'source':'[wheel+0x424]','caller':'FUN_00760d93','callee':'FUN_007538a0','callee_scalar_writes':['child+0xd4..+0xf4','child+0x18/+0x20/+0x28'],'transitive_exact_child_call':'FUN_007ba630','transitive_derived_child_call':'FUN_007ba7e0','exact_child_persistence_found':False,'wheel_root_reconstruction_found':False},
  'wheel_508_interior':{'source':'wheel+0x508','consumer':'FUN_007b1790 stack param1','consumer_register':'EDI','consumer_pointer_persistence_found':False,'consumer_forwards_pointer':False,'wheel_root_reconstruction_found':False},
  'wheel_9b0_interior':{'source':'wheel+0x9b0','consumer':'FUN_00753710 receiver','consumer_register':'ESI','consumer_pointer_persistence_found':False,'consumer_forwards_pointer':False,'wheel_root_reconstruction_found':False}},
 'machine_anchors':A,'adjudication':{'p13a_fun00760d93_derived_alias_subset_complete':True,'fun00760d93_derived_alias_pointer_persistence_found':False,'fun00760d93_derived_alias_wheel_root_reconstruction_found':False,'fun00760d93_derived_alias_selected_target_writer_found':False,'other_derived_aliases_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'reconstructed_wheel_pointers_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes only derived aliases emitted by the merged FUN_00760d93 trampolined exact-root path: children +0x420/+0x424 and interiors +0x508/+0x9b0.','FUN_007538a0 forwards the exact child receiver only to complete leaf FUN_007ba630; FUN_007ba7e0 receives the child but immediately derives child+0xd4/+0x18/+0x30 lanes rather than persisting the raw child pointer.','FUN_007b1790 consumes wheel+0x508 as a stack pointer and never copies/stores/forwards it. FUN_00753710 consumes wheel+0x9b0 as receiver and performs scalar writes only.','Independent FUN_00757318 interior aliases and callback/indirect surfaces remain open; no global gate is promoted.'],'next_step':'Close FUN_00757318 interior aliases (+0x5e8/+0x610/+0x638/+0x6a0/+0x6c0), then compose derived-alias coverage.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
