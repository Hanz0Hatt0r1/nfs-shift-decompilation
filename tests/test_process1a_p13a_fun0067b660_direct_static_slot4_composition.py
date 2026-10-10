import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'compose_p1a_fun0067b660_direct_static_slot4.py'
E=ROOT/'evidence'/'p1a_p13a_fun0067b660_direct_static_slot4_composition.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_slot4_comp',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_two_frontier_candidates_are_composed():
 p=data();c=p['slot4_candidate_composition'];assert p['format']=='SHIFT.P1A.P13AFun0067b660DirectStaticSlot4Composition/1'
 assert c['frontier_candidate_count']==2 and c['frontier_candidates']==['0x006022ee','0x006145c4']
 assert c['raw_memory_immediate_cleanup_candidate_count']==0
 assert c['candidate_0x006022ee']['exact_target']=='FUN_00600f60' and c['candidate_0x006022ee']['targets_FUN_0067b660'] is False
 assert c['candidate_0x006145c4']['static_initializer_result_count']==2 and c['candidate_0x006145c4']['static_initializer_results_target_animation_vtable'] is False
def test_creg_exact_scalar_has_no_external_seed():
 s=data()['creg_static_seed_surface'];assert s['command']=='0x63726567' and s['whole_image_raw_dword_occurrence_count']==1
 assert s['external_exact_creg_scalar_seed_count']==0 and s['direct_fun005ffc50_creg_call_count']==0
 assert s['exact_fun005ffc50_va_pointer_count']==0 and s['exact_fun005ffc50_rva_pointer_count']==0
 assert s['sole_exact_scalar_use']=={'site':'0x005ffc69','instruction':'cmp eax,0x63726567'}
def test_authority_and_formats_are_pinned():
 p=data();m=mod();assert p['authority']['retail_executable_sha256']==m.SHA and p['authority']['inputs']==m.FORMATS
def test_narrow_composition_gate_only():
 a=data()['adjudication'];assert a['p13a_fun0067b660_direct_static_immediate_slot4_surface_complete'] is True
 assert a['direct_static_immediate_slot4_target_fun0067b660_found'] is False
 assert a['direct_static_candidate_006022ee_fun0067b660_rejected'] is True and a['two_static_registry_initializer_results_fun0067b660_rejected'] is True
 assert a['external_exact_creg_scalar_seed_found'] is False
 for k in ['dynamic_registry_reconstructed_or_indirect_registration_ruled_out','fun0067b660_callback_argument_provenance_complete','callbacks_and_indirect_entry_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
