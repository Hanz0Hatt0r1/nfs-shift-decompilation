#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
from typing import Any, Mapping, Sequence

FORMAT = "SHIFT.BMWPrimaryPlayerFirstBootstrapRenderRootDelta/1"
RELATION_FORMAT = "SHIFT.OuterVehicleBMWVHFRootRelation/1"
SESSION_FORMAT = "SHIFT.BMWOffset33bNativeSessionSelection/1"
PROGRAM = "SHIFT.exe"
PE_MD5 = "705af8b420e5eb1e3834ac43d5533c6b"
SOURCE_SHA256 = "512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"
VEHICLE = "BMW_M3_E36"
SESSION_TARGET = "Silverstone+BMW_M3_E36"
CANONICAL_VHF = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
FUNCTIONS = {
 "0x0074ddc3": ("FUN_0074ddc3",957,"__fastcall","1b8f7a6602190fdd97b5a3d410495c8ff92b3a8b854a703459427b1ff548e4a6"),
 "0x0074e760": ("FUN_0074e760",101,"__fastcall","ee0a3baf733559a20dd134f43707056898cf73dd31be7d15a51922e1c02260b4"),
 "0x0078ef00": ("FUN_0078ef00",1538,"__fastcall","f981daa8164768121875faef1a053d93a6f78e6a3901a73aa32904b875ddb8e1"),
 "0x00795d60": ("FUN_00795d60",8797,"__fastcall","c587cae5d3d8f99afed40fe0c059c8c60bc9cc45d9ee644f5e90e2e1f5a8eb14"),
 "0x00797fd0": ("FUN_00797fd0",612,"__thiscall","b8f3cb6525e0742e2afefd31ca51dd050a9d869444526ce03df41067ecb3eeb8"),
 "0x00798df0": ("FUN_00798df0",1581,"__thiscall","88904019443d1ea4edaf5a3ef40dd5abfe9e28109ab0b1f09296388f36026e16"),
 "0x0079bfd0": ("FUN_0079bfd0",445,"__fastcall","06e730897a4a85d93a5f33765fd15b0c52708fb2c864c290804024b109a3d950"),
}
ORIGIN_GLOBALS=(0x00C16AB0,0x00C16AB8,0x00C16AC0); SWITCH_FLAG=0x00C19DB9
EXPECTED_INCOMING={
 "0x0079bfd0":{("0x0079c1c0","0x0079c1e1")},
 "0x00798df0":{("0x0074ddc3","0x0074de12")},
 "0x00795d60":{("0x00798df0","0x007990ed")},
 "0x0078ef00":{("0x0074bfd0","0x0074c05b"),("0x00794a30","0x00794a81"),("0x0079b2d0","0x0079b323")},
}

def _require(c: bool,m: str)->None:
 if not c: raise ValueError(m)
def _mapping(v:Any,l:str)->Mapping[str,Any]: _require(isinstance(v,Mapping),f"{l} missing"); return v
def _json(p:Path)->Mapping[str,Any]: return _mapping(json.loads(p.read_text()),str(p))
def _jsonl(p:Path)->list[dict[str,Any]]: return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]

def parse_pe_sections(image:bytes):
 _require(len(image)>=0x100,"PE image too small"); pe=struct.unpack_from("<I",image,0x3c)[0]
 _require(image[pe:pe+4]==b"PE\0\0","PE signature drift"); n=struct.unpack_from("<H",image,pe+6)[0]; osz=struct.unpack_from("<H",image,pe+20)[0]; opt=pe+24
 _require(struct.unpack_from("<H",image,opt)[0]==0x10b,"expected PE32 image"); base=struct.unpack_from("<I",image,opt+28)[0]; st=opt+osz; out=[]
 for i in range(n):
  o=st+i*40; name=image[o:o+8].split(b"\0",1)[0].decode(); vs,va,rs,rp=struct.unpack_from("<IIII",image,o+8); out.append({"name":name,"virtual_size":vs,"virtual_address":va,"raw_size":rs,"raw_pointer":rp})
 return base,out

def zero_fill_fact(base:int,secs:Sequence[Mapping[str,Any]],va:int)->dict[str,Any]:
 rva=va-base
 for s in secs:
  start=int(s["virtual_address"]); vs=int(s["virtual_size"])
  if start<=rva<start+vs:
   off=rva-start; rs=int(s["raw_size"]); return {"address":f"0x{va:08x}","section":str(s["name"]),"section_offset":f"0x{off:x}","section_virtual_size":f"0x{vs:x}","section_raw_size":f"0x{rs:x}","image_loader_zero_fill":off>=rs}
 raise ValueError(f"VA 0x{va:08x} outside PE sections")

def _file_va(base,secs,off):
 for s in secs:
  rp=int(s["raw_pointer"]); rs=int(s["raw_size"])
  if rp<=off<rp+rs:return base+int(s["virtual_address"])+(off-rp),str(s["name"])
 return None

def absolute_reference_sites(image:bytes,base:int,secs,va:int):
 needle=struct.pack("<I",va); out=[]; start=0
 while True:
  off=image.find(needle,start)
  if off<0:break
  m=_file_va(base,secs,off)
  if m: out.append({"pattern_va":f"0x{m[0]:08x}","section":m[1]})
  start=off+1
 return out

def _function_rows(rows):
 got={str(r.get("address") or "").lower():r for r in rows if str(r.get("address") or "").lower() in FUNCTIONS}; _require(set(got)==set(FUNCTIONS),"required retail function fingerprint row missing")
 for a,e in FUNCTIONS.items():
  r=got[a]; _require((r.get("name"),r.get("size"),r.get("calling_convention"),r.get("mnemonic_sha256"))==e,f"{a} function fingerprint drift")

def _incoming(rows,target): return {(str(r.get("from_function") or "").lower(),str(r.get("instruction") or "").lower()) for r in rows if str(r.get("to") or "").lower()==target and r.get("indirect") is False}
def validate_callgraph(rows):
 out={}
 for t,e in EXPECTED_INCOMING.items():
  a=_incoming(rows,t); _require(a==e,f"incoming direct-call set drift for {t}: {sorted(a)}"); out[t]=[{"from_function":c,"instruction":i} for c,i in sorted(a)]
 return out

def function_body(src:str,name:str)->str:
 needle=name+"("; pos=0
 while True:
  st=src.find(needle,pos); _require(st>=0,f"{name} definition missing from source"); brace=src.find("{",st); semi=src.find(";",st)
  if brace>=0 and (semi<0 or brace<semi):
   d=0
   for i in range(brace,len(src)):
    if src[i]=="{":d+=1
    elif src[i]=="}":
     d-=1
     if d==0:return src[st:i+1]
   raise ValueError(f"{name} body unterminated")
  pos=st+len(needle)

def validate_source(src:str,*,require_hash:bool=True):
 if require_hash:_require(hashlib.sha256(src.encode()).hexdigest()==SOURCE_SHA256,"retail decompiler source SHA-256 drift")
 restart=function_body(src,"FUN_0074ddc3"); role=function_body(src,"FUN_00797fd0"); init=function_body(src,"FUN_00798df0"); ctor=function_body(src,"FUN_0079bfd0"); delta=function_body(src,"FUN_00795d60"); cfg=function_body(src,"FUN_0074e760"); writer=function_body(src,"FUN_0078ef00"); base=function_body(src,"FUN_00a62690"); restart_cfg=function_body(src,"FUN_0074d640")
 markers=["FUN_00797fd0((void *)(*unaff_ESI + 0x340),*(int *)(iVar1 + 0x10),'\\0',1);","if (*(int *)(iVar1 + 0x10) == 0)","DAT_00c10b34 = unaff_ESI;","FUN_00798df0((void *)(iVar6 + 0x340),(char)*(undefined4 *)(unaff_EBP + 0xc));"]
 for m in markers:_require(m in restart,f"Restart source marker drift: {m}")
 _require(all(restart.index(markers[i])<restart.index(markers[i+1]) for i in range(3)),"Restart role/InitVehicle order drift")
 _require("FUN_0078ef00(" not in restart[:restart.index(markers[-1])],"origin writer entered Restart->InitVehicle prefix")
 for body,label in ((restart_cfg,"FUN_0074d640"),(role,"FUN_00797fd0"),(base,"FUN_00a62690")):
  _require("FUN_0078ef00(" not in body,f"origin writer entered {label}")
  for off in ("0x19c","0x1a0","0x1a4"):_require(off not in body,f"{label} touches render-root delta field {off}")
 call="FUN_00795d60(this,param_1,local_2390,*(void **)((int)this + 0x1d00),param_1);"; _require(call in init,"InitVehicle delta call drift"); pre=init[:init.index(call)]; _require("FUN_0078ef00(" not in pre,"origin writer entered InitVehicle prefix")
 _require("*(int *)((int)this + 0x234) = param_1;" in role,"Vehicle+0x234 role store drift"); _require("*(undefined4 *)(param_1 + 0x10) = 0;" in cfg,"spawn config +0x10 initializer drift")
 for i in (0x67,0x68,0x69):_require(f"param_1[0x{i:x}] = 0;" in ctor,f"constructor zero missing at 0x{i:x}")
 for m in ("if (*(int *)((int)param_1 + 0x234) == 0)","local_3c = local_28 - (float)_DAT_00c16ab0;","local_38 = *(float *)((int)param_1 + 0x1a0) - (float)_DAT_00c16ab8;","local_34 = *(float *)((int)param_1 + 0x1a4) - (float)_DAT_00c16ac0;","*(float *)((int)param_1 + 0x19c) = local_3c;","*(float *)((int)param_1 + 0x1a0) = local_38;","*(float *)((int)param_1 + 0x1a4) = local_34;"):_require(m in delta,f"primary-role delta marker drift: {m}")
 _require("(double *)&DAT_00c16ab0" in writer and "FUN_007afd20" in writer,"origin writer binding drift")
 return {"restart_role_code_source":"PhysicsParticipant spawn config +0x10","restart_zero_role_designates_primary_participant":True,"vehicle_role_code_field":"+0x234","vehicle_constructor_delta_zero_offsets":["+0x19c","+0x1a0","+0x1a4"],"primary_role_delta_formula":["new +0x19c = old +0x19c - DAT_00c16ab0","new +0x1a0 = old +0x1a0 - DAT_00c16ab8","new +0x1a4 = old +0x1a4 - DAT_00c16ac0"],"origin_writer":"FUN_0078ef00 -> FUN_007afd20(..., &DAT_00c16ab0, ...)","origin_writer_in_restart_to_initvehicle_prefix":False}

def validate_upstream(relation,session):
 _require(relation.get("format")==RELATION_FORMAT and relation.get("ready") is True,"outer/VHF relation not positive"); _require(relation.get("semantic_authority")=="Process 1","outer/VHF historical authority drift"); subj=_mapping(relation.get("subject"),"relation subject"); _require(subj.get("vehicle")==VEHICLE and str(subj.get("canonical_vhf") or "").lower()==CANONICAL_VHF,"relation subject drift"); rel=_mapping(relation.get("relation"),"relation"); _require(rel.get("kind")=="fixed_affine","outer/VHF relation is not fixed-affine"); _require(rel.get("relation_matrix_numeric_ready") is False,"upstream relation already has a numeric matrix"); h=_mapping(relation.get("handoff"),"relation handoff"); _require(h.get("outer_vehicle_root_to_VHF_vehicle_root_ready") is True and h.get("outer_vehicle_root_to_VHF_fixed_affine_delta_ready") is True and h.get("outer_vehicle_root_to_VHF_relation_numeric_matrix_ready") is False,"relation handoff drift")
 _require(session.get("format")==SESSION_FORMAT and session.get("ready") is True and session.get("vehicle")==VEHICLE and session.get("session_target")==SESSION_TARGET,"native session drift"); s=_mapping(session.get("selector"),"selector"); _require(s.get("source")=="explicit-native-vertical-slice-policy" and s.get("validated_against_retail_selector_domain") is True,"native selector drift")

def build_report(relation,session,function_rows,callgraph_rows,source,image,*,native_role,first_vehicle_bootstrap):
 validate_upstream(relation,session); _require(native_role=="primary-player" and first_vehicle_bootstrap is True,"proof scope is first primary-player bootstrap only"); _require(hashlib.md5(image).hexdigest()==PE_MD5,"retail SHIFT.exe MD5 drift"); _function_rows(function_rows); incoming=validate_callgraph(callgraph_rows); sp=validate_source(source); base,secs=parse_pe_sections(image); z=[zero_fill_fact(base,secs,a) for a in (*ORIGIN_GLOBALS,SWITCH_FLAG)]; _require(all(r["section"]==".data" and r["image_loader_zero_fill"] for r in z),"required globals are not PE zero-fill"); refs={f"0x{a:08x}":absolute_reference_sites(image,base,secs,a) for a in (*ORIGIN_GLOBALS,SWITCH_FLAG)}; _require([len(refs[k]) for k in ("0x00c16ab0","0x00c16ab8","0x00c16ac0","0x00c19db9")]==[2,1,1,2],"absolute xref count drift"); _require(all(r["section"]==".text" for rows in refs.values() for r in rows),"global xref escaped .text"); _require(absolute_reference_sites(image,base,secs,0x0078EF00)==[],"origin writer has absolute function-pointer reference")
 return {"format":FORMAT,"version":1,"status":"bmw-primary-player-first-bootstrap-render-root-delta-proven","ready":True,"vehicle":VEHICLE,"session_target":SESSION_TARGET,"semantic_authority":"single process","inputs":{"outer_vehicle_vhf_relation":RELATION_FORMAT,"native_session_selector":SESSION_FORMAT,"retail_program":PROGRAM},"native_bootstrap_policy":{"role":"primary-player","physics_participant_spawn_config_plus_0x10":0,"first_vehicle_bootstrap":True,"source":"explicit-native-vertical-slice-policy","validated_against_retail_restart_role_semantics":True,"retail_live_session_role_observed":False},"retail":{"program":PROGRAM,"md5":PE_MD5,"decompiler_source_sha256":SOURCE_SHA256,"function_fingerprints":{a:{"name":e[0],"size":e[1],"calling_convention":e[2],"mnemonic_sha256":e[3]} for a,e in FUNCTIONS.items()},"incoming_direct_calls":incoming},"bootstrap_provenance":{"source_proof":sp,"pe_zero_fill":{"image_base":f"0x{base:08x}","globals":z},"absolute_reference_sites":refs,"origin_vector_unique_reviewed_direct_writer":"FUN_0078ef00","origin_writer_direct_callers":["FUN_0074bfd0","FUN_00794a30","FUN_0079b2d0"],"origin_writer_absolute_function_pointer_refs":[],"selected_prefix":"first native primary-player PhysicsParticipant::Restart -> FUN_00797fd0(role=0) -> Vehicle::InitVehicle -> FUN_00795d60","origin_writer_reached_before_selected_delta_store":False,"constructor_old_delta":[0.0,0.0,0.0],"image_initial_origin_vector":[0.0,0.0,0.0],"primary_role_formula_evaluation":"old_delta - initial_origin"},"selected_numeric":{"delta_local_offsets":["+0x19c","+0x1a0","+0x1a4"],"delta_local":[0.0,0.0,0.0],"producer":"FUN_00795d60","scope":"first explicit native primary-player vehicle bootstrap before any origin-update path"},"handoff":{"BMW_primary_player_first_bootstrap_render_root_delta_numeric_ready":True,"outer_vehicle_root_to_VHF_vehicle_root_ready":True,"outer_vehicle_root_to_VHF_fixed_affine_delta_ready":True,"outer_vehicle_root_to_VHF_relation_numeric_matrix_ready":False,"BODY0_local_to_VHF_vehicle_root_numeric_matrix_ready":False,"BODY0_bind_frame_proof_ready":False,"vehicle_world_transform_ready":False,"consumer":"single-process S2 numeric outer->VHF evaluator, then S3 SHIFT.BMWBody0BindFrameProof/1"},"limits":{"first_primary_player_bootstrap_only":True,"delta_zero_claimed_for_restart_or_mode_switch":False,"delta_zero_claimed_for_non_primary_vehicle":False,"native_role_policy_is_retail_live_session_observation":False,"origin_vector_assumed_zero_after_first_origin_update":False,"VHF_root_numeric_matrix_consumed":False,"outer_vehicle_VHF_numeric_matrix_claimed":False,"BODY0_bind_frame_claimed":False,"runtime_capture_used":False,"original_game_executed":False},"next_blocker":{"id":"BMW-outer-VHF-numeric-relation-evaluation","required":"consume exact positive BMW VHF HIERARCHY Root row-vector matrix and delta_local=(0,0,0), evaluate finite outer->VHF matrix, then compose selected BODY0->outer matrix"}}

def main():
 p=argparse.ArgumentParser(); p.add_argument("relation",type=Path); p.add_argument("native_session",type=Path); p.add_argument("functions_jsonl",type=Path); p.add_argument("callgraph_jsonl",type=Path); p.add_argument("shift_c",type=Path); p.add_argument("shift_exe",type=Path); p.add_argument("--native-role",required=True,choices=("primary-player",)); p.add_argument("--first-vehicle-bootstrap",action="store_true"); p.add_argument("--json-out",type=Path); a=p.parse_args(); sb=a.shift_c.read_bytes(); _require(hashlib.sha256(sb).hexdigest()==SOURCE_SHA256,"retail decompiler source SHA-256 drift"); r=build_report(_json(a.relation),_json(a.native_session),_jsonl(a.functions_jsonl),_jsonl(a.callgraph_jsonl),sb.decode(),a.shift_exe.read_bytes(),native_role=a.native_role,first_vehicle_bootstrap=a.first_vehicle_bootstrap); text=json.dumps(r,indent=2,sort_keys=True)+"\n"; a.json_out.write_text(text) if a.json_out else print(text,end="")
if __name__=="__main__": main()
