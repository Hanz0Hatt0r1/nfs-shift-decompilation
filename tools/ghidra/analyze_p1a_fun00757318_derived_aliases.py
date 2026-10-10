#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun00757318DerivedAliasClosure/1'
UPSTREAM='SHIFT.P1A.P13AFun007572f0IndexedWheelRootLifetime/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TEXT_VA=0x401000;TEXT_RAW=0x400
RANGES={
 'fun00757318':(0x757318,0x757beb,'40e942861f5e15b40542c88c11f7b08131c0280d47cf43109889c3363bfbdcee'),
 'fun007a06a0':(0x7a06a0,0x7a07b7,'06bffad36d14d0a5a9c0e4774acaa1b04f5ea3cf1895f39d65c9d9a381b8cb02'),
 'fun007a0420':(0x7a0420,0x7a0451,'c1bb69f90c4bb2db3e12b615ed2b06d8af00ea4a21b2d7b627941000f1075b7f'),
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
def raw_receiver_escapes(rows,reg,start):
 bad=[]
 for a,m,o in rows:
  if a<=start:continue
  if m=='push' and o==reg:bad.append((a,m,o))
  if m in {'mov','lea'} and ',' in o:
   d,s=o.split(',',1)
   if s==reg:bad.append((a,m,o))
  if m=='xchg' and reg in o.split(','):bad.append((a,m,o))
 return bad
def analyze(exe:Path,upstream:Path):
 b=exe.read_bytes();sha=hashlib.sha256(b).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 u=json.loads(upstream.read_text())
 if u['format']!=UPSTREAM or not u['adjudication']['p13a_fun007572f0_indexed_wheel_root_lifetime_subset_complete']:raise AssertionError('upstream')
 expected={x['site'] for x in u['exact_root_lifetime']['derived_interior_aliases']}
 if expected!={'0x007573bc','0x0075740f','0x0075743a','0x007577b8','0x007577f6'}:raise AssertionError(expected)
 auth={};rows={};maps={}
 for n,(s,e,h) in RANGES.items():
  raw=b[TEXT_RAW+s-TEXT_VA:TEXT_RAW+e-TEXT_VA]
  if len(raw)!=e-s or hashlib.sha256(raw).hexdigest()!=h:raise AssertionError(('range',n))
  rr=dis(exe,s,e);rows[n]=rr;maps[n]={a:(m,o) for a,m,o in rr};auth[n]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 M=maps['fun00757318'];specs=[
  ('+0x610',0x7573bc,0x7573fd,'0x7a06a0'),('+0x638',0x75740f,0x757428,'0x7a06a0'),('+0x5e8',0x75743a,0x757453,'0x7a06a0'),
  ('+0x6a0',0x7577b8,0x7577e4,'0x7a0420'),('+0x6c0',0x7577f6,0x75780f,'0x7a0420')]
 aliases=[];A={}
 for off,lea,call,target in specs:
  req(M,lea,'lea',f'ecx,[edi{off}]');req(M,call,'call',target)
  aliases.append({'offset':off,'materialization':f'0x{lea:08x}','call':f'0x{call:08x}','consumer':'FUN_'+target[2:]})
  A[f'alias_{off[3:]}']=f'0x{lea:08x} lea ecx,[edi{off}]';A[f'call_{off[3:]}']=f'0x{call:08x} call {target}'
 C=maps['fun007a06a0'];req(C,0x7a06b1,'mov','esi,ecx');req(C,0x7a06cc,'lea','ecx,[ebp+0x10]');req(C,0x7a06d2,'call','0x753620');req(C,0x7a071f,'lea','ecx,[ebp-0x10]');req(C,0x7a0777,'call','0x7af310')
 bad=raw_receiver_escapes(rows['fun007a06a0'],'esi',0x7a06b1)
 if bad:raise AssertionError(('7a06a0 receiver escape',bad))
 # all calls after capture explicitly use ECX derived from stack-local state, not ESI.
 C2=maps['fun007a0420'];req(C2,0x7a0437,'fstp','QWORD PTR [ecx]');req(C2,0x7a044d,'pop','ebp');req(C2,0x7a044e,'ret','0x18')
 if any(m in {'call','jmp','push'} for _,m,_ in rows['fun007a0420']):raise AssertionError('7a0420 not leaf')
 # Neither consumer materializes a negative wheel-root displacement or writes bare receiver values.
 writes_06=['+0x0','+0x8','+0x10','+0x18','+0x20'];writes_04=['+0x0','+0x8','+0x10','+0x18']
 targets=[]
 for a in aliases:
  base=int(a['offset'],16)
  rel=writes_06 if a['consumer']=='FUN_7a06a0' else writes_04
  spans=[]
  for r in rel:
   x=base+int(r,16);spans.append(f'wheel+0x{x:x}')
  a['bounded_scalar_write_roots']=spans
  if any(0x538<=base+int(r,16)<=0x53f for r in rel):targets.append(a['offset'])
 if targets:raise AssertionError(('selected target overlap',targets))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':UPSTREAM,'ranges':auth},'aliases':aliases,'consumer_closure':{'FUN_007a06a0':{'source_offsets':['+0x5e8','+0x610','+0x638'],'complete_body':True,'receiver_capture':'ESI=ECX','receiver_pointer_persistence_found':False,'receiver_forwarded_to_callee':False,'bounded_receiver_write_offsets':writes_06},'FUN_007a0420':{'source_offsets':['+0x6a0','+0x6c0'],'complete_leaf':True,'receiver_pointer_persistence_found':False,'receiver_forwarded_to_callee':False,'bounded_receiver_write_offsets':writes_04}},'machine_anchors':A,'adjudication':{'p13a_fun00757318_derived_alias_subset_complete':True,'fun00757318_derived_alias_pointer_persistence_found':False,'fun00757318_derived_alias_wheel_root_reconstruction_found':False,'fun00757318_derived_alias_selected_target_writer_found':False,'other_derived_aliases_ruled_out':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'reconstructed_wheel_pointers_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes only the five interior aliases emitted by the merged FUN_007572f0/FUN_00757318 indexed-wheel path.','FUN_007a06a0 captures the interior receiver in ESI but every nested call is prepared with ECX pointing to stack-local/input state; bare ESI is never stored, pushed, copied, or forwarded.','FUN_007a0420 is a complete leaf that writes only scalar fields at +0/+8/+0x10/+0x18 relative to the interior receiver.','Other derived aliases outside the two newly closed materializer families, callback/indirect entry, reconstructed pointers and aggregate stored aliases remain fail-closed.'],'next_step':'Compose the merged exact-root and derived-alias closures to enumerate what still blocks the global runtime-generated/stored-alias gates.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('upstream',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.upstream);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
