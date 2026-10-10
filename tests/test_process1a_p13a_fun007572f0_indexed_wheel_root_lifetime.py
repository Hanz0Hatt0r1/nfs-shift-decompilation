import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_fun007572f0_indexed_wheel_root_lifetime.py'
E=ROOT/'evidence'/'p1a_p13a_fun007572f0_indexed_wheel_root_lifetime.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_7572',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def test_indexed_root_formula_and_entry_surface_are_exact():
 p=data();assert p['format']=='SHIFT.P1A.P13AFun007572f0IndexedWheelRootLifetime/1'
 assert p['entry_surface']=={'direct_FUN_007572f0_call_count':3,'direct_call_sites':['0x00761d96','0x00763349','0x0076335c']}
 r=p['indexed_root'];assert r['formula']=='vehicle_root + 0x400 + index*0xA80'
 assert r['slot0_root']=='HDVehicle+0x400' and r['slot1_root']=='HDVehicle+0xe80'
def test_only_exact_root_forward_is_closed_leaf():
 x=data()['exact_root_lifetime']
 assert x['explicit_bare_root_copy_count']==1 and x['explicit_bare_root_store_count']==0 and x['explicit_bare_root_push_count']==0
 assert x['exact_root_calls']==[{'call':'0x00757b87','prep':'0x00757b55','target':'0x752fc0'}]
 assert x['forward_leaf']=='FUN_00752fc0' and x['forward_leaf_is_complete'] is True and x['forward_leaf_root_persistence_found'] is False
 assert [a['site'] for a in x['derived_interior_aliases']]==['0x007573bc','0x0075740f','0x0075743a','0x007577b8','0x007577f6']
def test_machine_ranges_match_analyzer_constants():
 p=data();m=module();assert p['authority']['retail_executable_sha256']==m.SHA
 for n,(s,e,h) in m.RANGES.items():
  r=p['authority']['ranges'][n];assert r['start']==f'0x{s:08x}' and r['end_exclusive']==f'0x{e:08x}' and r['size']==e-s and r['sha256']==h
def test_narrow_gate_only():
 a=data()['adjudication'];assert a['p13a_fun007572f0_indexed_wheel_root_lifetime_subset_complete'] is True
 assert a['indexed_exact_wheel_root_materialization_found'] is True and a['indexed_exact_wheel_root_persistent_escape_found'] is False
 for k in ['runtime_generated_selected_wheel_pointer_stores_ruled_out','reconstructed_wheel_pointers_ruled_out','other_derived_aliases_ruled_out','stored_or_escaped_aliases_ruled_out','callbacks_and_indirect_entry_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
