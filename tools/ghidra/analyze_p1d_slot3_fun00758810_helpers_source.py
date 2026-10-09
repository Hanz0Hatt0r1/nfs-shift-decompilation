#!/usr/bin/env python3
"""Bound direct helper side effects for the FUN_00758810 slot3 branch."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3Fun00758810HelperEffects/1"
SOURCE_SHA256="512753a5f91898885263c91664a3d3fa3e07bfd58b72d3a5f89c402a00760ee9"

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()

def extract(text:str,start_sig:str,next_sig:str)->str:
 s=text.find(start_sig)
 if s<0: raise ValueError(f'missing {start_sig}')
 e=text.find(next_sig,s+len(start_sig))
 if e<0: raise ValueError(f'missing boundary after {start_sig}')
 return text[s:e]

def analyze(source:Path)->dict:
 digest=sha256(source)
 if digest!=SOURCE_SHA256: raise ValueError(f'unexpected SHIFT.exe.c SHA-256: {digest}')
 text=source.read_text(encoding='utf-8',errors='replace')
 aef=extract(text,'void __thiscall FUN_007aefb0(void *this,double *param_1,double *param_2)','void __thiscall FUN_007af010')
 add=extract(text,'void __fastcall FUN_00753590(double *param_1,double *param_2,double *param_3)','void __fastcall FUN_007535c0')
 scale=extract(text,'void __fastcall FUN_007535f0(double *param_1,double *param_2,double param_3)','void __thiscall FUN_00753620')
 body=extract(text,'void __thiscall FUN_007baaf0(void *this,double *param_1,double *param_2)','void __thiscall FUN_007bab70')
 for needle in ['*param_2 = (double)','param_2[1] = (double)','param_2[2] = (double)']:
  if needle not in aef: raise ValueError('FUN_007aefb0 output surface drift')
 for needle in ['*param_1 = *param_2 + *param_3;','param_1[1] = param_2[1] + param_3[1];','param_1[2] = param_2[2] + param_3[2];']:
  if needle not in add: raise ValueError('FUN_00753590 output surface drift')
 for needle in ['*param_1 = *param_2 * param_3;','param_1[1] = param_2[1] * param_3;','param_1[2] = param_3 * param_2[2];']:
  if needle not in scale: raise ValueError('FUN_007535f0 output surface drift')
 offsets=['0x48','0x50','0x58','0x60','0x68','0x70']
 for off in offsets:
  if f'((int)this + {off})' not in body: raise ValueError(f'FUN_007baaf0 missing BODY write {off}')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1D / P1.3D',
  'authority':{'platform':'PC retail 1.02','retail_decompiler_source_sha256':digest},
  'call_context':{'caller':'FUN_00758810','selected_target':'HDVehicle+0x28b8..+0x28bf'},
  'helpers':{
   'FUN_007aefb0':{'role':'matrix/vector transform','writes_only_output_param':True,'FUN_00758810_output_is_stack_local':True},
   'FUN_00753590':{'role':'3-double add','writes_only_output_param':True,'FUN_00758810_outputs_are_stack_local':True},
   'FUN_007535f0':{'role':'3-double scale','writes_only_output_param':True,'FUN_00758810_outputs_are_stack_local':True},
   'FUN_007baaf0':{'receiver':'chassis BODY0','direct_write_offsets':['+0x48','+0x50','+0x58','+0x60','+0x68','+0x70'],'writes_HDVehicle_slot3':False},
  },
  'adjudication':{'fun00758810_direct_helper_side_effect_surface_complete':True,'helper_selected_slot3_writer_found':False,'slot3_writer_provenance_proven':False,'p1_3d_complete':False,'external_provider_count':7},
  'limits':['This covers only the four direct non-CRT helpers invoked by FUN_00758810.','Chassis BODY0 is a separate pointed-to object; its offsets are not HDVehicle offsets.'],
 }

def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=analyze(a.source)
 except ValueError as e:p.error(str(e))
 t=json.dumps(r,indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(t,encoding='utf-8')
 else:print(t,end='')
 return 0
if __name__=='__main__':raise SystemExit(main())
