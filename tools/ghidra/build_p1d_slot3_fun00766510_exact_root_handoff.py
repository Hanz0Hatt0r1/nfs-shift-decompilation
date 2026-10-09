#!/usr/bin/env python3
"""Compose existing retail proofs for FUN_00766510 exact-HDVehicle callees into P1.3D.

This is an ownership bridge only. It consumes already-merged machine evidence and
never promotes numeric offset equality to selected object identity.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

FORMAT="SHIFT.P1D.Slot3Fun00766510ExactRootHandoff/1"
IDENTITY_FORMAT="SHIFT.P1A.P13ASlot01X87ReuseTrancheClosure/1"
TAIL_FORMAT="SHIFT.Fun00766510ResidualTailClosure/1"
PE_SHA256="eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1"

def load(path:Path,fmt:str)->dict:
 p=json.loads(path.read_text(encoding='utf-8'))
 if p.get('format')!=fmt or not p.get('ready'): raise ValueError(f'{path}: unexpected or unready contract')
 if p.get('authority',{}).get('retail_executable_sha256')!=PE_SHA256: raise ValueError(f'{path}: retail identity drift')
 return p

def build(identity_path:Path,tail_path:Path)->dict:
 identity=load(identity_path,IDENTITY_FORMAT); tail=load(tail_path,TAIL_FORMAT)
 rows={r.get('function'):r for r in identity.get('resolved',[])}
 if rows.get('FUN_00766510',{}).get('domain')!='HDVehicle root': raise ValueError('FUN_00766510 HDVehicle identity not proven upstream')
 pair=tail.get('auxiliary_pair_scheduling',{})
 if pair.get('caller')!='FUN_00766510' or pair.get('callee')!='FUN_00758fc0': raise ValueError('auxiliary pair identity drift')
 expected=[('first_call','0x00766da5','HDVehicle+0x37d8'),('second_call','0x00766dba','HDVehicle+0x3858')]
 calls=[]
 for key,site,record in expected:
  row=pair.get(key,{})
  if row.get('callsite')!=site or row.get('record')!=record or row.get('receiver')!='ECX=ESI=HDVehicle': raise ValueError(f'{key} exact-root transfer drift')
  calls.append({'callsite':site,'callee':'FUN_00758fc0','receiver':'HDVehicle','record_argument':record,'reference_vector':row.get('reference_vector')})
 apply=pair.get('callee_accumulator_application',{})
 offsets=apply.get('caller_accumulator_offsets')
 if offsets!=['0x40a0','0x40a8','0x40b0']: raise ValueError('FUN_00758fc0 write surface drift')
 if any(int(x,16)<=0x28bf and int(x,16)+7>=0x28b8 for x in offsets): raise ValueError('unexpected target overlap')
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1D / P1.3D','upstream_contracts':[IDENTITY_FORMAT,TAIL_FORMAT],
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':PE_SHA256,'machine_transfer_adjudicates_upstream':True,'upstream_contracts_consumed_not_reowned':True},
  'selected_slot3':{'absolute_target':'HDVehicle+0x28b8','width':'f64/qword'},
  'exact_root_calls':calls,
  'callee_effect':{'function':'FUN_00758fc0','proven_hdvehicle_write_offsets':['+0x40a0','+0x40a8','+0x40b0'],'selected_target_overlap':False,'machine_cross_callsite':apply.get('cross_callsite')},
  'adjudication':{'slot3_fun00766510_fun00758fc0_exact_root_pair_complete':True,'fun00758fc0_selected_slot3_writer_found':False,'deeper_direct_aliases_ruled_out':False,'indirect_callback_aliases_ruled_out':False,'slot3_writer_provenance_proven':False,'p1_3d_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7},
  'limits':['Only the two exact-HDVehicle FUN_00758fc0 calls proven by the residual-tail contract are closed here.','Other FUN_00766510 direct callees, descendants, stored aliases and indirect/callback carriers remain open.','P1A/P1.1 contracts retain their original ownership.'],
  'next_step':'Trace remaining exact HDVehicle/wheel receiver callees from lifecycle roots; prioritize any call that can derive or store the selected wheel root.'}

def main()->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('identity',type=Path);p.add_argument('tail',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 try:r=build(a.identity,a.tail)
 except ValueError as e:p.error(str(e))
 t=json.dumps(r,indent=2,sort_keys=True)+'\n'; a.output.write_text(t,encoding='utf-8') if a.output else print(t,end=''); return 0
if __name__=='__main__': raise SystemExit(main())
