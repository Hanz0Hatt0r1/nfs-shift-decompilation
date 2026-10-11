import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'compose_p1a_fun005ffc50_direct_absolute_writable_slots.py'
E=ROOT/'evidence'/'p1a_p13a_fun005ffc50_direct_absolute_writable_slots.json'
def mod():
 s=importlib.util.spec_from_file_location('p1a_wcomp',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text(encoding='utf-8'))
def test_complete_direct_absolute_data_slot_partition():
 p=data();i=p['direct_absolute_writable_transfer_inventory'];assert p['format']=='SHIFT.P1A.P13AFun005ffc50DirectAbsoluteWritableTransferComposition/1'
 assert i['unique_slot_count']==259 and i['transfer_count']==334 and i['all_unique_slots_partitioned'] is True
 g=i['groups'];assert g['nvapi_queryinterface_table']=={'slot_count':255,'transfer_count':255,'internal_FUN_005ffc50_provider_found':False}
 assert g['writable_callback_pair']=={'slot_count':2,'transfer_count':77,'direct_static_FUN_005ffc50_value_found':False}
def test_two_fixed_bridge_slots_are_not_target_and_have_no_direct_writers():
 rows=data()['direct_absolute_writable_transfer_inventory']['groups']['fixed_bridge_slots']['rows']
 assert rows['0x00b87b64']=={'initial_target':'0x00901707','direct_transfer_count':1,'direct_transfer_kind':'jmp','direct_absolute_writer_count':0,'targets_FUN_005ffc50':False}
 assert rows['0x00b87b68']=={'initial_target':'0x0090162a','direct_transfer_count':1,'direct_transfer_kind':'jmp','direct_absolute_writer_count':0,'targets_FUN_005ffc50':False}
def test_authority_composes_exact_upstream_contracts():
 p=data();m=mod();assert p['authority']['retail_executable_sha256']==m.SHA
 assert p['authority']['input_contracts']=={'callback_pair':m.PAIR,'nvapi_table':m.NVAPI}
def test_narrow_composition_keeps_non_absolute_writable_sources_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_direct_absolute_writable_indirect_transfer_slot_inventory_complete'] is True
 assert a['direct_absolute_writable_transfer_internal_fun005ffc50_provider_found'] is False
 for k in ['register_loaded_or_aliased_writable_slots_ruled_out','writable_memory_or_runtime_fun005ffc50_entry_ruled_out','writable_callback_pair_indirect_or_alias_writers_ruled_out','return_value_fun005ffc50_provenance_ruled_out','unbounded_multi_edge_or_phi_reconstruction_ruled_out','encoded_or_reconstructed_callback_entry_ruled_out','dynamic_registry_reconstructed_or_indirect_registration_ruled_out','callbacks_and_indirect_entry_ruled_out','fun0067b660_callback_argument_provenance_complete','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
