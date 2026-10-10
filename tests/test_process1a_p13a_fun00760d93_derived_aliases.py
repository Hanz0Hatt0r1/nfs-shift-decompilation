import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun00760d93_derived_aliases.py'
E=ROOT/'evidence'/'p1a_p13a_fun00760d93_derived_alias_closure.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_760d93_alias',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def test_alias_inventory_is_exact():
 p=data();assert p['format']=='SHIFT.P1A.P13AFun00760d93DerivedAliasClosure/1'
 assert set(p['aliases'])=={'wheel_420_child','wheel_424_child','wheel_508_interior','wheel_9b0_interior'}
 assert p['aliases']['wheel_420_child']['source']=='[wheel+0x420]'
 assert p['aliases']['wheel_424_child']['source']=='[wheel+0x424]'
 assert p['aliases']['wheel_508_interior']['source']=='wheel+0x508'
 assert p['aliases']['wheel_9b0_interior']['source']=='wheel+0x9b0'
def test_child_and_interior_pointers_do_not_persist_or_reconstruct_root():
 p=data()['aliases']
 for k in ['wheel_420_child','wheel_424_child']:
  assert p[k]['exact_child_persistence_found'] is False
  assert p[k]['wheel_root_reconstruction_found'] is False
 for k in ['wheel_508_interior','wheel_9b0_interior']:
  assert p[k]['consumer_pointer_persistence_found'] is False
  assert p[k]['consumer_forwards_pointer'] is False
  assert p[k]['wheel_root_reconstruction_found'] is False
def test_machine_ranges_are_hash_pinned():
 p=data();m=module();assert p['authority']['retail_executable_sha256']==m.SHA
 for n,(s,e,h) in m.RANGES.items():
  r=p['authority']['ranges'][n];assert r['start']==f'0x{s:08x}' and r['end_exclusive']==f'0x{e:08x}' and r['size']==e-s and r['sha256']==h
def test_only_narrow_derived_alias_gate_promotes():
 a=data()['adjudication'];assert a['p13a_fun00760d93_derived_alias_subset_complete'] is True
 assert a['fun00760d93_derived_alias_pointer_persistence_found'] is False
 assert a['fun00760d93_derived_alias_wheel_root_reconstruction_found'] is False
 assert a['fun00760d93_derived_alias_selected_target_writer_found'] is False
 for k in ['other_derived_aliases_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','reconstructed_wheel_pointers_ruled_out','stored_or_escaped_aliases_ruled_out','callbacks_and_indirect_entry_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
