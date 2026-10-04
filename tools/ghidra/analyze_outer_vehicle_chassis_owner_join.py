#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any, Mapping

FORMAT='SHIFT.OuterVehicleChassisOwnerJoin/1'
INSTRUCTION_FORMAT='SHIFT.GhidraFunctionInstructions/2'
DB_FORMAT='SHIFT.GhidraEvidenceDatabase/1'
PROGRAM='SHIFT.exe'
PE_MD5='705af8b420e5eb1e3834ac43d5533c6b'

HD_INIT='0x0076df50'
CHASSIS_INIT='0x007ac4d0'
MATRIX_HELPER='0x007aef50'
CONTROL='0x007633b0'
POST='0x007ac2f0'
FORWARDER='0x007afb60'
LEAF='0x007876e0'
SOLVER='0x007615c0'

JOIN_TARGETS=(HD_INIT,CHASSIS_INIT,MATRIX_HELPER)
PRIOR_TARGETS=(LEAF,FORWARDER,POST,CONTROL)
COUNTS={HD_INIT:387,CHASSIS_INIT:704,MATRIX_HELPER:33,LEAF:21,FORWARDER:21,POST:90,CONTROL:89}
NAMES={a:f'FUN_{a[2:]}' for a in (*JOIN_TARGETS,*PRIOR_TARGETS)}
FINGERPRINTS={
 HD_INIT:'73a0d9d46d5d1bfd58068d2f72e91b77cf8c31cadb27745ba75b646901834dda',
 CHASSIS_INIT:'912218c717ebba3ab6185f1ca2758a3a7233a49b7d336939e162bcb3964bc525',
 MATRIX_HELPER:'4f20a5f630bb6182c44699f505011f5a1958a87f4433400b7776ffd1dc740c51',
 CONTROL:'34643530b03a2868818cec0b31ed9f0f03ca146df2c1e915e846b88033aaebfe',
 POST:'01f0b0a953c9f3dedc501d659b4a5cc952d3a4330eef92f154e3ad9ace85c7ba',
 FORWARDER:'93c1afd52632f79c7019e6533ea7049ccf83717f589e521fabe0cfb433cbf12f',
 LEAF:'6dd7d4522a98ffc6eb0bdb39a5f2fde5869579297f12342ce199e9ffbb1ffa48',
}
STRING_WITNESSES={
 '0x00ab5b74':('car body','0x007ac504'),
 '0x00abc55c':('CHASSIS','0x007acba8'),
 '0x00b0c6d8':('.joi.xml','0x007acc55'),
}
POST_POSE_SOURCE_FIELDS=(0x90,0x94,0x98,0x160,0x164,0x168,0x178)


def addr(v:Any)->str:
 if isinstance(v,int): return f'0x{v:08x}'
 m=re.search(r'0x[0-9a-f]+',str(v or '').lower())
 if not m: raise ValueError(f'not address: {v!r}')
 return f'0x{int(m.group(0),16):08x}'

def compact(v:Any)->str: return re.sub(r'\s+','',str(v or '')).lower()

def sha256_file(p: Path) -> str:
 h = hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda: f.read(1 << 20), b''):
   h.update(chunk)
 return h.hexdigest()

def read_json(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text())
 if not isinstance(v,dict): raise ValueError(f'{p}: expected object')
 return v

def read_jsonl(p:Path)->list[dict[str,Any]]:
 out=[]
 for n,line in enumerate(p.read_text().splitlines(),1):
  if not line.strip(): continue
  v=json.loads(line)
  if not isinstance(v,dict): raise ValueError(f'{p}:{n}: expected object')
  out.append(v)
 return out

def load_db(root:Path)->tuple[dict[str,dict[str,Any]],dict[str,dict[str,Any]]]:
 b=read_json(root/'binary.json')
 if b.get('format')!=DB_FORMAT or b.get('program_name')!=PROGRAM or b.get('executable_md5')!=PE_MD5:
  raise ValueError('retail binary identity drift')
 wanted=set(FINGERPRINTS)
 funcs={}
 for r in read_jsonl(root/'functions.jsonl'):
  a=str(r.get('address') or '').lower()
  if a in wanted: funcs[a]=r
 missing=wanted-set(funcs)
 if missing: raise ValueError(f'missing function rows: {sorted(missing)}')
 for a,h in FINGERPRINTS.items():
  r=funcs[a]
  if r.get('mnemonic_sha256')!=h: raise ValueError(f'{a}: mnemonic fingerprint drift')
  if r.get('external') is True or r.get('thunk') is True: raise ValueError(f'{a}: not concrete retail function')
 strings={}
 for r in read_jsonl(root/'strings_xrefs.jsonl'):
  a=str(r.get('address') or '').lower()
  if a in STRING_WITNESSES: strings[a]=r
 for a,(value,xref) in STRING_WITNESSES.items():
  r=strings.get(a)
  if not r or r.get('value')!=value or xref not in (r.get('xrefs') or []) or CHASSIS_INIT not in (r.get('functions') or []):
   raise ValueError(f'{a}: string witness drift')
 return funcs,strings

def load_export(p:Path,targets:tuple[str,...])->dict[str,dict[str,Any]]:
 rows={}
 for n,v in enumerate(read_jsonl(p),1):
  if v.get('format')!=INSTRUCTION_FORMAT or v.get('program')!=PROGRAM or v.get('found') is not True:
   raise ValueError(f'{p}:{n}: invalid instruction row')
  a=addr(v.get('requested'))
  f=v.get('function')
  if not isinstance(f,Mapping) or addr(f.get('address'))!=a or f.get('name')!=NAMES[a]: raise ValueError(f'{a}: metadata drift')
  ins=v.get('instructions')
  if not isinstance(ins,list) or v.get('instruction_count')!=len(ins) or len(ins)!=COUNTS[a]: raise ValueError(f'{a}: instruction count drift')
  rows[a]=v
 if set(rows)!=set(targets): raise ValueError(f'{p}: target set drift')
 return rows

def by(row): return {addr(x.get('address')):x for x in row['instructions']}
def req_text(b:dict[str,Mapping[str,Any]],site:str,*parts:str):
 x=b.get(site)
 if x is None: raise ValueError(f'missing {site}')
 t=compact(x.get('text'))
 for p in parts:
  if compact(p) not in t: raise ValueError(f'{site}: expected {p!r}, got {x.get("text")!r}')
def direct_target(x:Mapping[str,Any])->str|None:
 if str(x.get('mnemonic') or '').upper()!='CALL': return None
 for c in list(x.get('flows') or [])+list(x.get('operands') or []):
  try: return addr(c)
  except ValueError: pass
 return None
def req_call(b,site,target):
 x=b.get(site)
 if x is None or direct_target(x)!=target: raise ValueError(f'{site}: expected call {target}')

def analyze(db:Path,prior_p:Path,join_p:Path)->dict[str,Any]:
 funcs,strings=load_db(db)
 prior=load_export(prior_p,PRIOR_TARGETS)
 join=load_export(join_p,JOIN_TARGETS)

 h=by(join[HD_INIT])
 req_text(h,'0x0076df6e','mov','esi','ecx')
 req_text(h,'0x0076e236','mov','ecx','esi'); req_call(h,'0x0076e238',SOLVER)
 req_text(h,'0x0076e243','mov','eax','[esi+0x3fe8]')
 req_text(h,'0x0076e249','mov','edx','[esi+0x66b4]')
 req_text(h,'0x0076e24f','lea','ecx','[eax+0x10c]')
 req_text(h,'0x0076e255','push','ecx')
 req_text(h,'0x0076e256','mov','ecx','[eax]')
 req_text(h,'0x0076e258','push','0x1')
 req_text(h,'0x0076e25a','push','edx')
 req_text(h,'0x0076e25b','add','ecx','0x340')
 req_call(h,'0x0076e261',CHASSIS_INIT)

 c=by(prior[CONTROL])
 req_text(c,'0x007633d1','mov','esi','ecx')
 req_text(c,'0x007634d1','mov','edx','[esi+0x3fe8]')
 req_text(c,'0x007634d7','mov','ecx','[edx]')
 req_text(c,'0x007634d9','add','ecx','0x340')
 req_call(c,'0x007634df',POST)

 m=join[MATRIX_HELPER]['instructions']
 if any(str(x.get('mnemonic') or '').upper()=='CALL' for x in m): raise ValueError('matrix helper unexpectedly calls another function')
 mt='\n'.join(compact(x.get('text')) for x in m)
 for off in (0,4,8,0xc,0x10,0x14,0x18,0x1c,0x20):
  token='[ecx]' if off==0 else f'[ecx+0x{off:x}]'
  if token not in mt: raise ValueError(f'matrix helper missing {token}')
 for off in (0,4,8):
  token='[edx]' if off==0 else f'[edx+0x{off:x}]'
  if token not in mt: raise ValueError(f'matrix helper missing output {token}')
 for x in m:
  ops=x.get('operands') or []
  if ops and '[' in str(ops[0]) and 'ecx' in compact(ops[0]) and str(x.get('mnemonic') or '').upper() in {'MOV','FST','FSTP','MOVSS','MOVSD'}:
   raise ValueError('matrix helper writes receiver')

 ci=by(join[CHASSIS_INIT])
 req_text(ci,'0x007ac4fb','mov','edi','ecx')
 req_text(ci,'0x007aca9c','lea','ecx','[edi+0x30]'); req_call(ci,'0x007aca9f','0x007519d0')
 req_text(ci,'0x007acc14','mov','ecx','[edi+0x34]'); req_call(ci,'0x007acc1a','0x00777cd0')
 req_text(ci,'0x007acc25','lea','ecx','[edi+0x534]')
 req_text(ci,'0x007acca1','lea','ecx','[edi+0x534]'); req_call(ci,'0x007acca7','0x007a5a40')
 req_text(ci,'0x007accbd','lea','ecx','[edi+0x534]'); req_call(ci,'0x007accc3','0x007a3d60')
 direct_writes=[]
 write_mn={'MOV','FST','FSTP','MOVSS','MOVSD'}
 for x in join[CHASSIS_INIT]['instructions']:
  ops=x.get('operands') or []
  if not ops or str(x.get('mnemonic') or '').upper() not in write_mn: continue
  d=compact(ops[0]); mm=re.search(r'\[edi\+0x([0-9a-f]+)\]',d)
  if mm:
   direct_writes.append({'instruction':addr(x.get('address')),'offset':f'+0x{int(mm.group(1),16):x}','mnemonic':str(x.get('mnemonic')).upper()})
 write_offsets={int(x['offset'][1:],16) for x in direct_writes}
 pose_intersection=sorted(write_offsets & set(POST_POSE_SOURCE_FIELDS))
 if pose_intersection: raise ValueError(f'chassis init unexpectedly directly writes post-transform pose fields: {pose_intersection}')

 p=by(prior[POST])
 expected_post={
  '0x007ac368':'+0x160','0x007ac378':'+0x164','0x007ac384':'+0x168',
  '0x007ac36e':'+0x178','0x007ac3a4':'+0x90','0x007ac3b1':'+0x94','0x007ac3bb':'+0x98'
 }
 for site,off in expected_post.items(): req_text(p,site,f'[esi{off}]')

 return {
  'format':FORMAT,'version':1,'status':'chassis-owner-join-ready','ready':True,
  'retail':{'program':PROGRAM,'md5':PE_MD5},
  'dependencies':['SHIFT.OuterVehicleOwnerCandidateRoles/1 (FUN_007633b0 proven-HDVehicle-control-bridge)'],
  'inputs':{'owner_candidate_instruction_export_sha256':sha256_file(prior_p),'chassis_join_instruction_export_sha256':sha256_file(join_p)},
  'owner_join':{
   'HDVehicle_Init_entry_receiver_saved_in':'ESI',
   'solver_setup_receiver':'HDVehicle entry ECX',
   'chassis_init_callsite':'0x0076e261','chassis_init_callee':CHASSIS_INIT,
   'chassis_init_receiver_expression':'*([HDVehicle+0x3fe8])+0x340',
   'chassis_init_stack_argument_machine_sources':['[HDVehicle+0x66b4]','0x1','[HDVehicle+0x3fe8]+0x10c'],
   'control_post_transform_callsite':'0x007634df','control_post_transform_callee':POST,
   'control_post_transform_receiver_expression':'*([HDVehicle+0x3fe8])+0x340',
   'same_HDVehicle_relative_child_expression':True,
   'cross_invocation_pointer_equality_proven':False,
   'frame_identity_proven':False,
  },
  'forwarded_branch':{
   'function':MATRIX_HELPER,'role':'call-free-3x3-matrix-vector-leaf',
   'receiver_matrix_float_offsets':['+0x0','+0x4','+0x8','+0xc','+0x10','+0x14','+0x18','+0x1c','+0x20'],
   'output_float_offsets':['+0x0','+0x4','+0x8'],'owner_forward_edge_present':False,
   'receiver_write_present':False,'excluded_from_owner_search':True,
  },
  'chassis_init':{
   'function':CHASSIS_INIT,'entry_receiver_saved_in':'EDI',
   'semantic_string_witnesses':[{'address':a,'value':v,'xref':x} for a,(v,x) in STRING_WITNESSES.items()],
   'embedded_owner_edges':[{'offset':'+0x30','callee':'0x007519d0'},{'offset':'+0x34','callee':'0x00777cd0','kind':'loaded-pointer'},{'offset':'+0x534','callees':['0x0049f980','0x007a5a40','0x007a3d60']}],
   'direct_receiver_writes':direct_writes,
   'post_transform_pose_source_fields':[f'+0x{x:x}' for x in POST_POSE_SOURCE_FIELDS],
   'direct_write_intersection_with_post_transform_pose_source_fields':[],
   'direct_bind_pose_writer_proven':False,
  },
  'handoff':{
   'forwarded_007afb60_branch_eliminated':True,
   'HDVehicle_car_body_CHASSIS_child_domain_joined_to_runtime_post_transform_domain':True,
   'join_strength':'same-HDVehicle-relative-receiver-expression-and-concrete-init/update-callees',
   'outer_owner_search_has_parallel_anonymous_thiscall_branch':False,
   'outer_vehicle_root_to_VHF_vehicle_root_ready':False,
   'BODY0_bind_frame_proof_ready':False,
   'vehicle_world_transform_ready':False,
  },
  'blocker':{
   'id':'BODY0-bind-frame-source-writer-still-unproven',
   'reason':'car-body/CHASSIS initializer does not directly write the runtime post-transform pose-source fields and no VHF vehicle-root frame join is present',
   'required_next_join':'return to the source-backed BODY construction side-effect/write chain; do not continue the eliminated 0x007aef50 branch or infer identity from the +0x340 owner join',
  },
  'scope':{
   'original_game_executed':False,'new_runtime_capture_required':False,
   'upstream_HDVehicle_control_role_revalidated_here':False,
   'Ghidra_fastcall_metadata_used_as_semantic_ABI':False,
   'same_relative_expression_promoted_to_cross_invocation_pointer_equality':False,
   'car_body_label_promoted_to_VHF_frame_identity':False,
   'absence_of_direct_pose_field_writes_promoted_to_absence_of_indirect_writers':False,
  }
 }

def main(argv=None):
 ap=argparse.ArgumentParser()
 ap.add_argument('ghidra_export',type=Path); ap.add_argument('owner_candidate_export',type=Path); ap.add_argument('chassis_join_export',type=Path); ap.add_argument('--json-out',type=Path)
 a=ap.parse_args(argv); r=analyze(a.ghidra_export,a.owner_candidate_export,a.chassis_join_export); text=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.json_out: a.json_out.write_text(text)
 else: print(text,end='')
 return 0
if __name__=='__main__': raise SystemExit(main())
