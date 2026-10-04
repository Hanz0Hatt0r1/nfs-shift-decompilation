from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_outer_vehicle_chassis_owner_join.py'
SPEC=importlib.util.spec_from_file_location('outer_vehicle_chassis_owner_join',TOOL)
assert SPEC and SPEC.loader
m=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(m)

def ins(a,text,mn=None,flows=None,ops=None):
 return {'address':a,'mnemonic':mn or text.split()[0],'text':text,'operands':ops or [],'flows':flows or [],'pcode':[]}
def call(a,t): return ins(a,f'CALL {t}','CALL',[t],[t])
def pad(rows,count,base):
 used={int(x['address'],16) for x in rows}; cur=base
 while len(rows)<count:
  if cur not in used: rows.append(ins(f'0x{cur:08x}','NOP','NOP')); used.add(cur)
  cur+=1
 return sorted(rows,key=lambda x:int(x['address'],16))
def write_export(path, targets, bodies):
 with path.open('w') as f:
  for a in targets:
   body=pad(list(bodies.get(a,[])),m.COUNTS[a],int(a,16))
   f.write(json.dumps({'format':m.INSTRUCTION_FORMAT,'program':m.PROGRAM,'requested':a,'found':True,'function':{'address':a,'name':m.NAMES[a],'size':1,'calling_convention':'__thiscall'},'instruction_count':len(body),'instructions':body})+'\n')

def make_db(root:Path):
 root.mkdir()
 (root/'binary.json').write_text(json.dumps({'format':m.DB_FORMAT,'program_name':m.PROGRAM,'executable_md5':m.PE_MD5}))
 with (root/'functions.jsonl').open('w') as f:
  for a,h in m.FINGERPRINTS.items():
   f.write(json.dumps({'address':a,'name':m.NAMES[a],'external':False,'thunk':False,'mnemonic_sha256':h})+'\n')
 with (root/'strings_xrefs.jsonl').open('w') as f:
  for a,(value,xref) in m.STRING_WITNESSES.items():
   f.write(json.dumps({'address':a,'value':value,'xrefs':[xref],'functions':[m.CHASSIS_INIT]})+'\n')

def prior_bodies():
 return {
  m.CONTROL:[ins('0x007633d1','MOV ESI,ECX',ops=['ESI','ECX']),ins('0x007634d1','MOV EDX,dword ptr [ESI + 0x3fe8]',ops=['EDX','dword ptr [ESI + 0x3fe8]']),ins('0x007634d7','MOV ECX,dword ptr [EDX]',ops=['ECX','dword ptr [EDX]']),ins('0x007634d9','ADD ECX,0x340',ops=['ECX','0x340']),call('0x007634df',m.POST)],
  m.POST:[ins('0x007ac368','FLD float ptr [ESI + 0x160]'),ins('0x007ac36e','LEA EAX,[ESI + 0x178]'),ins('0x007ac378','FLD float ptr [ESI + 0x164]'),ins('0x007ac384','FLD float ptr [ESI + 0x168]'),ins('0x007ac3a4','FLD float ptr [ESI + 0x90]'),ins('0x007ac3b1','FLD float ptr [ESI + 0x94]'),ins('0x007ac3bb','FLD float ptr [ESI + 0x98]')],
  m.LEAF:[],m.FORWARDER:[]}

def join_bodies():
 mat=[]
 for i,off in enumerate((0,4,8,0xc,0x10,0x14,0x18,0x1c,0x20)):
  token='[ECX]' if off==0 else f'[ECX + 0x{off:x}]'; mat.append(ins(f'0x{0x7aef50+i:08x}',f'FLD float ptr {token}','FLD'))
 for i,off in enumerate((0,4,8)):
  token='[EDX]' if off==0 else f'[EDX + 0x{off:x}]'; mat.append(ins(f'0x{0x7aef80+i:08x}',f'FSTP float ptr {token}','FSTP',[ ],[f'float ptr {token}']))
 return {
  m.HD_INIT:[ins('0x0076df6e','MOV ESI,ECX',ops=['ESI','ECX']),ins('0x0076e236','MOV ECX,ESI',ops=['ECX','ESI']),call('0x0076e238',m.SOLVER),ins('0x0076e243','MOV EAX,dword ptr [ESI + 0x3fe8]'),ins('0x0076e249','MOV EDX,dword ptr [ESI + 0x66b4]'),ins('0x0076e24f','LEA ECX,[EAX + 0x10c]'),ins('0x0076e255','PUSH ECX'),ins('0x0076e256','MOV ECX,dword ptr [EAX]'),ins('0x0076e258','PUSH 0x1'),ins('0x0076e25a','PUSH EDX'),ins('0x0076e25b','ADD ECX,0x340'),call('0x0076e261',m.CHASSIS_INIT)],
  m.CHASSIS_INIT:[ins('0x007ac4fb','MOV EDI,ECX'),ins('0x007aca9c','LEA ECX,[EDI + 0x30]'),call('0x007aca9f','0x007519d0'),ins('0x007acc14','MOV ECX,dword ptr [EDI + 0x34]'),call('0x007acc1a','0x00777cd0'),ins('0x007acc25','LEA ECX,[EDI + 0x534]'),ins('0x007acca1','LEA ECX,[EDI + 0x534]'),call('0x007acca7','0x007a5a40'),ins('0x007accbd','LEA ECX,[EDI + 0x534]'),call('0x007accc3','0x007a3d60'),ins('0x007ace13','FSTP float ptr [EDI + 0x4c]','FSTP',ops=['float ptr [EDI + 0x4c]'])],
  m.MATRIX_HELPER:mat}

def fixture(tmp_path, mutate=None):
 db=tmp_path/'db'; make_db(db); prior=tmp_path/'prior.jsonl'; join=tmp_path/'join.jsonl'; pb=prior_bodies(); jb=join_bodies()
 if mutate: mutate(pb,jb)
 write_export(prior,m.PRIOR_TARGETS,pb); write_export(join,m.JOIN_TARGETS,jb)
 return db,prior,join

def test_real_shape_narrows_to_one_child_domain_without_bind_claim(tmp_path):
 db,prior,join=fixture(tmp_path)
 r=m.analyze(db,prior,join)
 assert r['ready'] is True
 assert r['owner_join']['same_HDVehicle_relative_child_expression'] is True
 assert r['forwarded_branch']['excluded_from_owner_search'] is True
 assert r['handoff']['HDVehicle_car_body_CHASSIS_child_domain_joined_to_runtime_post_transform_domain'] is True
 assert r['handoff']['outer_owner_search_has_parallel_anonymous_thiscall_branch'] is False
 assert r['handoff']['BODY0_bind_frame_proof_ready'] is False
 assert r['chassis_init']['direct_write_intersection_with_post_transform_pose_source_fields']==[]

def test_rejects_child_receiver_expression_drift(tmp_path):
 def mutate(pb,jb):
  for x in jb[m.HD_INIT]:
   if x['address']=='0x0076e25b': x['text']='ADD ECX,0x344'
 db,prior,join=fixture(tmp_path,mutate)
 with pytest.raises(ValueError,match='0x340'): m.analyze(db,prior,join)

def test_rejects_forwarded_helper_that_starts_forwarding(tmp_path):
 def mutate(pb,jb): jb[m.MATRIX_HELPER].append(call('0x007aef7f','0x00700000'))
 db,prior,join=fixture(tmp_path,mutate)
 with pytest.raises(ValueError,match='unexpectedly calls'): m.analyze(db,prior,join)

def test_direct_pose_source_write_blocks_negative_writer_claim(tmp_path):
 def mutate(pb,jb): jb[m.CHASSIS_INIT].append(ins('0x007ac500','FSTP float ptr [EDI + 0x90]','FSTP',ops=['float ptr [EDI + 0x90]']))
 db,prior,join=fixture(tmp_path,mutate)
 with pytest.raises(ValueError,match='pose fields'): m.analyze(db,prior,join)
