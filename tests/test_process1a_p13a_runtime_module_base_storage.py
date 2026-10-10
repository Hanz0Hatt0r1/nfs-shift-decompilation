import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_runtime_module_base_storage.py'
EVIDENCE=ROOT/'evidence'/'p1a_p13a_runtime_module_base_storage_frontier.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_module_base',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(EVIDENCE.read_text(encoding='utf-8'))
def test_vtable_slots_and_machine_anchors():
 m=mod(); assert m.VTABLE==0x00AAB2D8
 assert m.VTABLE_SLOTS=={0x80:0x00886B70,0x84:0x00886C00,0xA0:0x00886C60,0xA4:0x00886C70}
 assert m.EXPECTED_REL32[0x0090481C]==0x00A69160
 assert m.EXPECTED_REL32[0x00A69197]==0x00886980
 assert m.EXPECTED_REL32_JMP[0x0040CA60]==0x0040B870
 assert m.EXPECTED_REL32_JMP[0x0040A010]==0x00D33990
def test_two_runtime_storage_fields_are_exact():
 p=data(); assert p['format']=='SHIFT.P1A.P13ARuntimeModuleBaseStorageFrontier/1'
 assert p['startup_seed']['value']=='0x00400000'
 assert p['runtime_receiver']['fixed_object']=='0x00bbf960'
 assert p['runtime_receiver']['vtable']=='0x00aab2d8'
 assert p['runtime_receiver']['resolved_slots']=={'+0x80':'0x00886b70','+0x84':'0x00886c00','+0xa0':'0x00886c60','+0xa4':'0x00886c70'}
 assert [x['destination'] for x in p['module_base_sinks']]==['0x00bfa4fc / singleton+0x4','0x00bfa504 / singleton+0xc']
def test_positive_storage_does_not_promote_carrier_or_slot_gates():
 a=data()['adjudication']; assert a['p13a_startup_module_base_storage_subset_complete'] is True
 assert a['runtime_module_base_persistence_found'] is True and a['runtime_module_base_storage_field_count']==2
 assert a['runtime_module_base_fields_are_carrier_pointers'] is False
 assert a['runtime_module_base_getter_consumer_paths_complete'] is False
 for k in ['manual_imagebase_plus_rva_pointer_construction_ruled_out','encoded_or_reconstructed_carrier_pointers_ruled_out','runtime_generated_or_copied_carrier_pointers_ruled_out','runtime_callback_registration_ruled_out','incoming_indirect_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
