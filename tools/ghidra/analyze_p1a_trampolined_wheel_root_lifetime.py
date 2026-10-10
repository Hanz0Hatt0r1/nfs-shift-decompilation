#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re,sqlite3,subprocess
from pathlib import Path
FORMAT='SHIFT.P1A.P13ATrampolinedWheelRootLifetime/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
SQLITE_SHA='ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e'
TOPO='SHIFT.P1A.P13ASlot01SameFunctionTopologyMachineClosure/1'
GLOBAL='SHIFT.GlobalVehicleBodyOwnerIdentity/1'
TEXT_VA=0x401000; TEXT_RAW=0x400
RANGES={
 'fun007653f0':(0x7653f0,0x7653f8,'186c430d078f7ca53c5210117b069a805b9c8f0bed280bf71c06a5f04ab683a4'),
 'entry_trampoline':(0x419031,0x41903c,'da250265c2741065a467312ac54ea653005a48200d5dca8f361641395487d252'),
 'fun007653f9':(0x7653f9,0x765461,'b6b2fd78772d2db662bd953f51747413305859448776904422cb62029888154e'),
 'fun00760d70':(0x760d70,0x760d91,'25379836160fa14a909fb49e19ffbe7616942afb0264e70fc44fe90d64ee7ca5'),
 'root_trampoline':(0x43dbbd,0x43dbc9,'ef7624958f7133103e5f319b09a48680c1307b7aaa9100f7b7080b6bf5f6d657'),
 'fun00760d93':(0x760d93,0x760f79,'c5dc2f0564fcefd31dab2555f7fa910758739cc9e95a1ac8029f995ea6d088f1'),
}
INST=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
DIRECT=re.compile(r'^0x([0-9a-fA-F]+)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def dis(exe,s,e):
 p=subprocess.run(['objdump','-d','-Mintel',f'--start-address=0x{s:x}',f'--stop-address=0x{e:x}',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 out=[]
 for line in p.stdout.splitlines():
  m=INST.match(line)
  if m: out.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 return out
def full_dis(exe):
 p=subprocess.run(['objdump','-d','-Mintel',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 for line in p.stdout.splitlines():
  m=INST.match(line)
  if m: yield int(m.group(1),16),m.group(2).lower(),norm(m.group(3))
def req(M,a,m,o=''):
 got=M.get(a); exp=(m,norm(o))
 if got!=exp:raise AssertionError((hex(a),got,exp))
 return f'0x{a:08x} {m} {exp[1]}'.rstrip()
def analyze(exe,db,topology,global_id):
 blob=exe.read_bytes(); sha=hashlib.sha256(blob).hexdigest(); dbsha=hashlib.sha256(db.read_bytes()).hexdigest()
 if sha!=SHA or dbsha!=SQLITE_SHA: raise ValueError((sha,dbsha))
 top=json.loads(topology.read_text()); glob=json.loads(global_id.read_text())
 if top['format']!=TOPO or glob['format']!=GLOBAL: raise ValueError('upstream format')
 if glob['identity_join']['global_vehicle_address']!='0x00c13700' or not glob['identity_join']['global_vehicle_component_base_identity_ready']:raise AssertionError('global vehicle identity')
 cand={x['function']:x for x in top['candidate_adjudication']}
 for n in ['FUN_00765850','FUN_00765aa0']:
  if n not in cand or not any('FUN_007653f0 is invoked on the vehicle root' in x for x in cand[n]['evidence']):raise AssertionError(n)
 auth={}; maps={}
 for name,(s,e,h) in RANGES.items():
  off=TEXT_RAW+s-TEXT_VA; raw=blob[off:off+e-s]
  if len(raw)!=e-s or hashlib.sha256(raw).hexdigest()!=h:raise AssertionError(('range drift',name))
  rows=dis(exe,s,e); maps[name]={a:(m,o) for a,m,o in rows};auth[name]={'start':f'0x{s:08x}','end_exclusive':f'0x{e:08x}','size':e-s,'sha256':h}
 M=maps['fun007653f0']; anchors={}
 anchors['vehicle_capture']=req(M,0x7653f1,'mov','esi,ecx');anchors['entry_trampoline_jump']=req(M,0x7653f3,'jmp','0x419031')
 M=maps['entry_trampoline'];anchors['slot0_body_pointer_load']=req(M,0x419031,'mov','eax,DWORD PTR [esi+0x824]');anchors['materializer_continuation']=req(M,0x419037,'jmp','0x7653f9')
 M=maps['fun007653f9']; specs=[
  (0,0x400,0x7653fa,[(0x765400,'call')]),
  (1,0xe80,0x76540c,[(0x765412,'call')]),
  (2,0x1900,0x76541f,[(0x765428,'call'),(0x765448,'call')]),
  (3,0x2380,None,[(0x76543a,'call'),(0x76545a,'call')]),
 ]; hand=[]
 for slot,off,site,trans in specs:
  if site: req(M,site,'lea',f'ecx,[esi+0x{off:x}]')
  for t,k in trans:
   if slot==3: req(M,t-6,'lea',f'ecx,[esi+0x{off:x}]')
   req(M,t,k,'0x760d70'); hand.append({'slot':slot,'root_offset':f'+0x{off:x}','materialization':f'0x{(site if site else t-6):08x}','transfer':f'0x{t:08x}','kind':k})
 M=maps['fun00760d70'];anchors['root_receiver_capture']=req(M,0x760d8a,'mov','esi,ecx');anchors['root_trampoline_jump']=req(M,0x760d8c,'jmp','0x43dbbd')
 M=maps['root_trampoline'];anchors['root_flag_test']=req(M,0x43dbbd,'cmp','BYTE PTR [esi+0x504],0x0');anchors['root_body_continuation']=req(M,0x43dbc4,'jmp','0x760d93')
 sites=[]
 for a,m,o in full_dis(exe):
  if m=='call' and o=='0x7653f0': sites.append(a)
 if sites!=[0x765831,0x765944,0x765ae8,0x7712c6]:raise AssertionError(('entry surface',sites))
 con=sqlite3.connect(db);c=con.cursor(); abi={}; call_targets=[]
 for a,(m,o) in maps['fun00760d93'].items():
  if m=='call' and (dm:=DIRECT.match(o)): call_targets.append((a,int(dm.group(1),16)))
 for target in sorted({t for _,t in call_targets}):
  row=c.execute('select name,raw_json from functions where lower(address)=?',(f'0x{target:08x}',)).fetchone()
  if not row:raise AssertionError(('missing callee',hex(target)))
  r=json.loads(row[1]); abi[f'0x{target:08x}']={'name':row[0],'calling_convention':r.get('calling_convention'),'signature':r.get('signature')}
 con.close()
 if any(v['calling_convention'] not in {'__thiscall','__fastcall','__cdecl','__stdcall'} for v in abi.values()):raise AssertionError(abi)
 exact=[]; interiors=[]; children=[]; combined=[]
 combined.extend((a,m,o) for a,(m,o) in maps['root_trampoline'].items());combined.extend((a,m,o) for a,(m,o) in maps['fun00760d93'].items())
 for a,m,o in combined:
  if m=='push' and o=='esi': exact.append((a,m,o))
  if m in {'mov','lea'} and ',' in o:
   dst,src=o.split(',',1)
   if src=='esi':exact.append((a,m,o))
   if m=='mov' and dst.startswith('DWORD PTR [') and src=='esi':exact.append((a,m,o))
   if m=='lea' and '[esi+' in src:interiors.append({'site':f'0x{a:08x}','operands':o})
   if m=='mov' and src in {'DWORD PTR [esi+0x420]','DWORD PTR [esi+0x424]'}:children.append({'site':f'0x{a:08x}','operands':o})
  if m=='xchg' and 'esi' in o.split(','):exact.append((a,m,o))
 if exact:raise AssertionError(('exact root escape',exact))
 raw_ecx=[]; rows=dis(exe,0x760d93,0x760f79)
 for i,(a,m,o) in enumerate(rows):
  if m!='call':continue
  for pa,pm,po in reversed(rows[max(0,i-8):i]):
   if pm in {'mov','lea'} and po.startswith('ecx,'):
    if po=='ecx,esi':raw_ecx.append((a,pa,po))
    break
 if raw_ecx:raise AssertionError(raw_ecx)
 return {'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A','authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'ghidra_sqlite_sha256':dbsha,'upstream_contracts':[TOPO,GLOBAL],'ranges':auth},'incoming_vehicle_root_surface':{'direct_FUN_007653f0_call_count':4,'direct_call_sites':[f'0x{x:08x}' for x in sites],'upstream_vehicle_root_qualified_callers':['FUN_00765850','FUN_00765aa0'],'global_vehicle_address':'0x00c13700','other_direct_callers':['FUN_00765470','FUN_00770e80'],'note':'FUN_00765470 is reached from FUN_00770e80 with ECX restored from its vehicle-root ESI; FUN_00770e80 is the global outer-update receiver lane. This contract does not use those facts to widen global entry gates.'},'trampolined_materialization':{'vehicle_capture':'ESI=vehicle root','handoff_count':len(hand),'handoffs':hand,'distinct_slots':[0,1,2,3]},'exact_root_lifetime':{'capture':'0x00760d8a ESI=ECX exact wheel root','explicit_exact_root_store_count':0,'explicit_exact_root_push_count':0,'explicit_exact_root_register_copy_count':0,'call_with_explicit_ECX_equal_exact_root_count':0,'callee_abi':abi,'derived_interior_aliases':interiors,'child_pointer_loads':children,'derived_aliases_are_exact_root':False},'machine_anchors':anchors,'adjudication':{'p13a_trampolined_wheel_root_exact_lifetime_subset_complete':True,'trampolined_exact_wheel_root_materialization_found':True,'trampolined_exact_wheel_root_persistent_escape_found':False,'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,'reconstructed_wheel_pointers_ruled_out':False,'other_derived_aliases_ruled_out':False,'stored_or_escaped_aliases_ruled_out':False,'callbacks_and_indirect_entry_ruled_out':False,'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},'limits':['This closes exact wheel-root value persistence only across FUN_007653f0 -> FUN_00419031 -> FUN_007653f9 -> FUN_00760d70 -> FUN_0043dbbd -> FUN_00760d93.','The root remains live in callee-saved ESI while standard-convention callees execute. Machine code never explicitly forwards bare ESI; Ghidra ABI confirms those callees consume ECX/stack arguments rather than ESI.','Derived interior pointers such as wheel+0x508 and wheel+0x9b0 and child pointers [wheel+0x420]/[wheel+0x424] are positive derived aliases and remain outside this exact-root closure.','Global runtime-generated/reconstructed/stored-alias and callback/indirect gates remain fail-closed.'],'next_step':'Trace persistence of the positive wheel+0x508/wheel+0x9b0 and child-pointer aliases, then classify FUN_00757318 indexed wheel-root lifetime before changing global runtime-generated selected-wheel gates.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('sqlite',type=Path);ap.add_argument('topology',type=Path);ap.add_argument('global_identity',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args();r=analyze(a.executable,a.sqlite,a.topology,a.global_identity);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s) if a.output else print(s,end='')
if __name__=='__main__':main()
