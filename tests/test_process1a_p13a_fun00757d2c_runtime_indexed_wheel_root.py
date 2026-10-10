import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun00757d2c_runtime_indexed_wheel_root.py'
EVIDENCE=ROOT/'evidence'/'p1a_p13a_fun00757d2c_runtime_indexed_wheel_root_persistence.json'
UPSTREAM=ROOT/'evidence'/'global_vehicle_component_callsite_phase633.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_idxwheel',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EVIDENCE.read_text())
def test_runtime_identity_matches_merged_upstream():
 p=data();u=json.loads(UPSTREAM.read_text());cs=u['runtime_component_callsite'];r=p['runtime_identity']
 assert p['format']=='SHIFT.P1A.P13AFun00757d2cRuntimeIndexedWheelRootPersistence/1'
 assert p['authority']['upstream_runtime_identity_contract']==u['format']=='SHIFT.GlobalVehicleComponentCallsiteStatic/1'
 assert (r['caller'],r['call_address'],r['return_address'])==(cs['caller'],cs['call_address'],cs['return_address'])
 assert r['vehicle_base_address']==cs['vehicle_base_address']=='0x00c13700'
 assert r['core_entry_abi']=='ECX=vehicle, EAX=slot*0xa80'
 assert r['wheel_root_formula']=='vehicle + 0x400 + slot*0xa80'
def test_slot0_slot1_geometry_and_root_lifetime_are_exact():
 p=data();s=p['runtime_identity']['slots'];life=p['exact_root_lifetime']
 assert s[0]=={'slot':0,'wheel_root':'HDVehicle+0x400','selected_target':'HDVehicle+0x938..+0x93f'}
 assert s[1]=={'slot':1,'wheel_root':'HDVehicle+0xe80','selected_target':'HDVehicle+0x13b8..+0x13bf'}
 assert life['materialization']=='0x00757d2e'
 assert life['fast_path_kill']=='0x00757d51' and life['slow_path_kill']=='0x00757d99'
 assert life['root_value_nonstack_store_count']==0
 assert life['root_value_push_count']==0
 assert life['root_value_register_copy_count']==0
 assert life['root_value_call_or_jump_while_live_count']==0
def test_positive_reconstruction_does_not_promote_global_gates():
 a=data()['adjudication']
 assert a['p13a_fun00757d2c_runtime_indexed_wheel_root_subset_complete'] is True
 assert a['runtime_indexed_exact_wheel_root_materialization_found'] is True
 assert a['runtime_indexed_exact_wheel_root_persistent_escape_found'] is False
 assert a['runtime_indexed_exact_wheel_root_selected_slot0_or_slot1_store_found'] is False
 for k in ['runtime_generated_selected_wheel_pointer_stores_ruled_out','reconstructed_wheel_pointers_ruled_out','stored_or_escaped_aliases_ruled_out','callbacks_and_indirect_entry_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
def test_machine_authority_is_pinned():
 p=data()['authority'];m=module()
 assert p['machine_body_start']=='0x00757d2c' and p['machine_body_end_exclusive']=='0x00757e51'
 assert p['machine_body_size']==293
 assert p['machine_body_sha256']==m.BODY_SHA=='587dcc93159ef142ef57d18e657aa3078e5d2748db0febb4ecba32a286bc20fa'
 assert p['retail_executable_sha256']==m.SHA256
