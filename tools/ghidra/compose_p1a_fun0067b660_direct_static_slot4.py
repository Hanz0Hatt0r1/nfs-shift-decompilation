#!/usr/bin/env python3
"""Compose the bounded direct/static slot+4 surface relevant to FUN_0067b660."""
from __future__ import annotations
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path

FORMAT='SHIFT.P1A.P13AFun0067b660DirectStaticSlot4Composition/1'
SHA='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
FORMATS={
 'frontier':'SHIFT.P1A.P13AFun0067b660Slot4DispatchAbiFrontier/1',
 'static_registry':'SHIFT.P1A.P13ASlot4StaticRegistryInitializers/1',
 'direct_creg':'SHIFT.P1A.P13AFun005ffc50DirectCregEntryClosure/1',
 'secondary':'SHIFT.P1A.P13ASlot4Candidate6022eeCommUdpResolution/1',
}
CREG=0x63726567
CREG_BYTES=struct.pack('<I',CREG)
EXPECTED_CREG_RAW_OFFSET=0x001ff06a
EXPECTED_CREG_COMPARE=0x005ffc69
I=re.compile(r'^\s*([0-9a-fA-F]+):\s+(?:[0-9a-fA-F]{2}\s+)+\s*([a-zA-Z][a-zA-Z0-9]*)\s*(.*)$')
def norm(s):return re.sub(r'\s+',' ',s.strip()).replace(', ', ',')
def load(path,fmt):
 p=json.loads(path.read_text(encoding='utf-8'))
 if p.get('format')!=fmt:raise ValueError((path,p.get('format'),fmt))
 if not p.get('ready',True):raise AssertionError((path,'not ready'))
 return p
def occ(blob,pat):
 out=[];i=0
 while True:
  i=blob.find(pat,i)
  if i<0:return out
  out.append(i);i+=1
def creg_instruction(exe):
 p=subprocess.run(['objdump','-d','-Mintel','--start-address=0x5ffc50','--stop-address=0x5ffc85',str(exe)],capture_output=True,text=True,errors='replace',check=True)
 rows=[]
 for line in p.stdout.splitlines():
  m=I.match(line)
  if m:rows.append((int(m.group(1),16),m.group(2).lower(),norm(m.group(3))))
 hits=[(a,m,o) for a,m,o in rows if '0x63726567' in o]
 if hits!=[(EXPECTED_CREG_COMPARE,'cmp','eax,0x63726567')]:raise AssertionError(('creg instruction drift',hits))
 return {'site':'0x005ffc69','instruction':'cmp eax,0x63726567'}
def analyze(exe,frontier_path,static_registry_path,direct_creg_path,secondary_path):
 blob=exe.read_bytes();sha=hashlib.sha256(blob).hexdigest()
 if sha!=SHA:raise ValueError(sha)
 frontier=load(frontier_path,FORMATS['frontier']);static=load(static_registry_path,FORMATS['static_registry']);direct=load(direct_creg_path,FORMATS['direct_creg']);secondary=load(secondary_path,FORMATS['secondary'])
 inv=frontier['slot4_abi_inventory']['near_register_slot4_immediate_cleanup']
 calls=[x['call'] for x in inv]
 if calls!=['0x006022ee','0x006145c4']:raise AssertionError(('frontier candidate drift',calls))
 if frontier['slot4_abi_inventory']['raw_memory_slot4_immediate_cleanup']!=[]:raise AssertionError('raw memory candidate drift')
 rows=static['static_initializer_rows']
 if static['static_registration_count']!=2 or len(rows)!=2 or any(x['returned_object_vptr_is_animation_vptr'] for x in rows):raise AssertionError('static registry type drift')
 if not static['registry_initializer_result_path']['static_result_types_exclude_animation_vtable']:raise AssertionError('static registry exclusion drift')
 if static['registry_initializer_result_path']['dynamic_result_types_closed']:raise AssertionError('dynamic registry unexpectedly closed upstream')
 da=direct['adjudication'];ds=direct['direct_entry_surface'];pl=direct['static_pointer_literal_surface']
 if ds['direct_creg_call_count']!=0 or da['direct_fun005ffc50_creg_registration_found']:raise AssertionError('direct creg drift')
 if pl['exact_absolute_va_occurrence_count'] or pl['exact_rva_occurrence_count']:raise AssertionError('dispatcher static pointer drift')
 if not da['fun005ffc50_creg_requires_indirect_or_reconstructed_entry']:raise AssertionError('direct creg boundary drift')
 sa=secondary['adjudication'];ct=secondary['commudp_table']
 if not sa['p13a_slot4_candidate_006022ee_direct_static_commudp_subset_complete'] or not sa['slot4_candidate_006022ee_direct_static_target_resolved']:raise AssertionError('secondary resolution incomplete')
 if sa['slot4_candidate_006022ee_direct_static_targets_fun0067b660']:raise AssertionError('secondary unexpectedly animation')
 if ct['candidate_0x006022ee_exact_slot4_target_on_bounded_paths']!='FUN_00600f60':raise AssertionError('secondary target drift')
 raw=occ(blob,CREG_BYTES)
 if raw!=[EXPECTED_CREG_RAW_OFFSET]:raise AssertionError(('creg raw scalar drift',raw))
 ins=creg_instruction(exe)
 return {
  'format':FORMAT,'version':1,'ready':True,'owner':'Process 1A / P1.3A',
  'authority':{'platform':'PC retail 1.02','retail_executable_sha256':sha,'inputs':FORMATS},
  'slot4_candidate_composition':{
   'frontier_candidate_count':2,
   'frontier_candidates':['0x006022ee','0x006145c4'],
   'raw_memory_immediate_cleanup_candidate_count':0,
   'candidate_0x006022ee':{'direct_static_class':'CommUDP table family','exact_target':'FUN_00600f60','targets_FUN_0067b660':False,'reconstructed_or_runtime_entry_closed':False},
   'candidate_0x006145c4':{'static_initializer_result_count':2,'static_initializer_results_target_animation_vtable':False,'dynamic_registration_forwarder':'0x005ffc7a','direct_creg_registration_count':0,'dynamic_result_types_closed':False},
  },
  'creg_static_seed_surface':{
   'command':'0x63726567','whole_image_raw_dword_occurrence_count':1,'whole_image_raw_dword_occurrences':['0x001ff06a file offset'],
   'sole_exact_scalar_use':ins,'external_exact_creg_scalar_seed_count':0,
   'direct_fun005ffc50_creg_call_count':0,'exact_fun005ffc50_va_pointer_count':0,'exact_fun005ffc50_rva_pointer_count':0,
  },
  'adjudication':{
   'p13a_fun0067b660_direct_static_immediate_slot4_surface_complete':True,
   'direct_static_immediate_slot4_target_fun0067b660_found':False,
   'direct_static_candidate_006022ee_fun0067b660_rejected':True,
   'two_static_registry_initializer_results_fun0067b660_rejected':True,
   'external_exact_creg_scalar_seed_found':False,
   'dynamic_registry_reconstructed_or_indirect_registration_ruled_out':False,
   'fun0067b660_callback_argument_provenance_complete':False,
   'callbacks_and_indirect_entry_ruled_out':False,
   'encoded_or_reconstructed_callback_entry_ruled_out':False,
   'runtime_generated_selected_wheel_pointer_stores_ruled_out':False,
   'stored_or_escaped_aliases_ruled_out':False,
   'p13a_slot0_complete':False,'p13a_slot1_complete':False,'p1_3_control_producer_complete':False,'external_provider_count':7,
  },
  'limits':[
   'This composition closes only the direct/static immediate slot+4 candidate surface isolated by the upstream 16-instruction/caller-cleanup scanner.',
   '0x006022ee is rejected as FUN_0067b660 only on its bounded direct/static provenance; reconstructed/encoded/runtime-generated FUN_006022d0 entry remains open.',
   '0x006145c4 has two known static initializer result types and both are non-animation; dynamic registration at 0x005ffc7a remains open because FUN_005ffc50 can still be reached through an unproven indirect/reconstructed entry.',
   'The exact creg scalar occurs only in the dispatcher comparison itself, so there is no separate whole-image exact-immediate seed for a static creg caller; split/encoded/runtime command formation is not ruled out.',
   'No global callback, incoming-indirect, stored-alias, slot0, slot1, or aggregate P1.3 gate is promoted.'
  ],
  'next_step':'Focus P1.3A callback work on reconstructed/indirect entry to FUN_005ffc50 and dynamic registry initializer provenance; the direct/static immediate slot4 surface is now composed and closed.'
 }
def main():
 ap=argparse.ArgumentParser();ap.add_argument('executable',type=Path);ap.add_argument('--frontier',type=Path,required=True);ap.add_argument('--static-registry',type=Path,required=True);ap.add_argument('--direct-creg',type=Path,required=True);ap.add_argument('--secondary',type=Path,required=True);ap.add_argument('--output',type=Path)
 a=ap.parse_args();r=analyze(a.executable,a.frontier,a.static_registry,a.direct_creg,a.secondary);s=json.dumps(r,indent=2,sort_keys=True)+'\n';a.output.write_text(s,encoding='utf-8') if a.output else print(s,end='')
if __name__=='__main__':main()
