#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13AFun007572f0IndexedWheelRootLifetime/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
TOPO='SHIFT.P1A.P13ASlot01SameFunctionTopologyMachineClosure/1'
TEXT_VA=0x401000;TEXT_RAW=0x400
RANGES={
 'fun007572f0_entry':(0x7572f0,0x757315,'0fc3c9c378ac13ab76b1c603a708579d33622ad09c9296856e492183efb6194a'),
 'config_trampoline':(0x4066a5,0x4066b0,'81907fd68c7bd3f5f4f1ad91d1351b37ffeb3d810721924987dfb5aa176590d1'),
 'fun00757318_body':(0x757318,0x757beb,'40e942861f5e15b40542c88c11f7b08131c0280d47cf43109889c3363bfbdcee'),
 'fun00752fc0_leaf':(0x752fc0,0x752fe5,'830ecb8fa09bf20a07a8e269f4d44351dc167232bba00f5d9a7d931675d111cc'),
}
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe,s,e):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def req(M,a,m,o=''):
 got=M.get(a);exp=(m,norm(o))
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {m} {exp[1]}'.rstrip()
def analyze(exe:Path,topology:Path):
 b=exe.read_bytes();sha=hashlib.sha256(b).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 top=json.loads(topology.read_text())
 if top['format']!=TOPO:raise ValueError(top['format'])
 cand={x['function']:x for x in top['candidate_adjudication']}
 c=cand.get('FUN_00757318')
 if not c or c['class']!='wheel-configuration':raise AssertionError('upstream FUN_00757318 class')
 if not any('vehicle_root + 0x400 + index*0xA80' in x for x in c['evidence']):raise AssertionError('upstream root formula')
 auth={};maps={}
 for n,(s,e,h) in RANGES.items():
  off=TEXT_RAW+s-TEXT_VA;raw=b[off:off+e-s]
  if len(raw)!=e-s or hashlib.sha256(raw).hexdigest()!=h:raise AssertionError(('range drift',n))
  rows=dis(exe,s,e);maps[n]={a:(m,o) for a,m,o in rows};auth[n]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 A={};M=maps['fun007572f0_entry']
 A['vehicle_capture']=req(M,0x7572fe,'mov','edi,ecx');A['vehicle_stack_alias']=req(M,0x757300,'mov','DWORD PTR [ebp-0x4],edi')
 A['config01_trampoline']=req(M,0x75730a,'jmp','0x4066a5');A['config_other_load']=req(M,0x757312,'mov','eax,DWORD PTR [edi+0x2e48]')
 M=maps['config_trampoline'];A['config01_load']=req(M,0x4066a5,'mov','eax,DWORD PTR [edi+0x2e44]');A['config_join']=req(M,0x4066ab,'jmp','0x757310')
 M=maps['fun007572f0_entry'];A['config_thunk']=req(M,0x757310,'jmp','0x757318')
 M=maps['fun00757318_body'];A['index_reload']=req(M,0x757329,'mov','eax,DWORD PTR [ebp+0x8]');A['index_stride']=req(M,0x75733c,'imul','eax,eax,0xa80');A['root_materialization']=req(M,0x757348,'lea','edi,[eax+edi*1+0x400]');A['exact_root_forward']=req(M,0x757b55,'mov','ecx,edi');A['exact_root_leaf_call']=req(M,0x757b87,'call','0x752fc0')
 rows=dis(exe,0x757348,0x757beb);exact=[];inter=[];root_call=[]
 for i,(a,m,o) in enumerate(rows):
  if m=='push' and o=='edi':exact.append((a,m,o))
  if m in {'mov','lea'} and ',' in o:
   d,s=o.split(',',1)
   if s=='edi':exact.append((a,m,o))
   if m=='lea' and '[edi+' in s:inter.append({'site':f'0x{a:08x}','operands':o})
  if m=='xchg' and 'edi' in o.split(','):exact.append((a,m,o))
  if m=='call':
   for pa,pm,po in reversed(rows[max(0,i-16):i]):
    if pm in {'mov','lea'} and po.startswith('ecx,'):
     if po=='ecx,edi':root_call.append({'call':f'0x{a:08x}','prep':f'0x{pa:08x}','target':o})
     break
 if exact!=[(0x757b55,'mov','ecx,edi')]:raise AssertionError(('exact copies',exact))
 if root_call!=[{'call':'0x00757b87','prep':'0x00757b55','target':'0x752fc0'}]:raise AssertionError(root_call)
 L=maps['fun00752fc0_leaf'];leaf_rows=dis(exe,0x752fc0,0x752fe5)
 if any(m in {'call','jmp','push'} for _,m,_ in leaf_rows):raise AssertionError('leaf transfer')
 if any(m in {'mov','lea'} and ',' in o and o.split(',',1)[1]=='ecx' for _,m,o in leaf_rows):raise AssertionError('leaf copies root')
 if any(m=='mov' and o.endswith(',ecx') and o.startswith('DWORD PTR [') for _,m,o in leaf_rows):raise AssertionError('leaf stores root')
 A['leaf_return']=req(L,0x752fe4,'ret')
 direct_sites=[]
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 for line in p.stdout.splitlines():
  mm=I.match(line)
  if mm and mm.group(2).lower()=='call' and norm(mm.group(3))=='0x7572f0':direct_sites.append(int(mm.group(1),16))
 if direct_sites!=[0x761d96,0x763349,0x76335c]:raise AssertionError(('direct entry surface',direct_sites))
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'upstream_contract':TOPO,'ranges':auth},'entry_surface':{'direct_FUN_007572f0_call_count':3,'direct_call_sites':[f'0x{x:08x}' for x in direct_sites]},'indexed_root':{'formula':'vehicle_root + 0x400 + index*0xA80','vehicle_register_before_materialization':'EDI','index_source':'[EBP+0x8]','exact_root_register_after_0x00757348':'EDI','slot0_root':'HDVehicle+0x400','slot1_root':'HDVehicle+0xe80'},'exact_root_lifetime':{'explicit_bare_root_copy_count':1,'bare_root_copies':[{'site':'0x00757b55','operation':'ECX=EDI','consumer':'0x00757b87 FUN_00752fc0'}],'explicit_bare_root_store_count':0,'explicit_bare_root_push_count':0,'exact_root_call_count':1,'exact_root_calls':root_call,'forward_leaf':'FUN_00752fc0','forward_leaf_is_complete':True,'forward_leaf_root_persistence_found':False,'derived_interior_aliases':inter,'derived_aliases_are_exact_root':False},'machine_anchors':A,'adjudication':{'p13a_fun007572f0_indexed_wheel_root_lifetime_subset_complete':True,'indexed_exact_wheel_root_materialization_found':True,'indexed_exact_wheel_root_persistent_escape_found':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'reconstructed_wheel_pointers_ruled_out':False,'other_derived_aliases_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This consumes the merged same-function topology contract for semantic vehicle-root/index identity and independently machine-proves exact-root lifetime through the split FUN_007572f0/FUN_00757318 body.','The only bare exact-root forward is ECX=EDI into complete leaf FUN_00752fc0; that leaf performs only scalar FPU field writes relative to ECX and does not persist/copy/forward the root pointer.','Positive interior aliases wheel+0x610, +0x638, +0x5e8, +0x6a0 and +0x6c0 remain separate derived-alias work.','Global reconstructed/runtime-generated/stored-alias and callback/indirect gates remain fail-closed.'],'next_step':'Classify the positive interior aliases from FUN_00757318 and compose the now-closed exact-root materializer families before considering the global runtime-generated selected-wheel pointer gate.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('topology',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.topology);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
