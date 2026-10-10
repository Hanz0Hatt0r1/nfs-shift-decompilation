import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_trampolined_wheel_root_lifetime.py'
E=ROOT/'evidence'/'p1a_p13a_trampolined_wheel_root_lifetime.json'
def module():
 s=importlib.util.spec_from_file_location('p1a_tramp_root',TOOL);assert s and s.loader
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data():return json.loads(E.read_text())
def test_entry_surface_and_four_slot_materialization_are_frozen():
 p=data();assert p['format']=='SHIFT.P1A.P13ATrampolinedWheelRootLifetime/1'
 s=p['incoming_vehicle_root_surface'];assert s['direct_FUN_007653f0_call_count']==4
 assert s['direct_call_sites']==['0x00765831','0x00765944','0x00765ae8','0x007712c6']
 h=p['trampolined_materialization'];assert h['handoff_count']==6 and h['distinct_slots']==[0,1,2,3]
 assert [x['root_offset'] for x in h['handoffs'][:2]]==['+0x400','+0xe80']
def test_exact_root_does_not_explicitly_escape_but_derived_aliases_remain_positive():
 x=data()['exact_root_lifetime']
 assert x['explicit_exact_root_store_count']==0
 assert x['explicit_exact_root_push_count']==0
 assert x['explicit_exact_root_register_copy_count']==0
 assert x['call_with_explicit_ECX_equal_exact_root_count']==0
 assert x['derived_interior_aliases']==[
  {'operands':'edx,[esi+0x508]','site':'0x00760ea3'},
  {'operands':'ecx,[esi+0x9b0]','site':'0x00760f22'}]
 assert len(x['child_pointer_loads'])==7
def test_machine_abi_and_ranges_are_pinned():
 p=data();m=module();assert p['authority']['retail_executable_sha256']==m.SHA
 assert p['authority']['ghidra_sqlite_sha256']==m.SQLITE_SHA
 assert set(p['exact_root_lifetime']['callee_abi'])=={'0x00753710','0x007538a0','0x007b1130','0x007b1790','0x007b19f0'}
 for n,(s,e,h) in m.RANGES.items():
  r=p['authority']['ranges'][n];assert r['start']==f'0x{s:08x}' and r['end_exclusive']==f'0x{e:08x}' and r['size']==e-s and r['sha256']==h
def test_only_narrow_gate_promotes():
 a=data()['adjudication'];assert a['p13a_trampolined_wheel_root_exact_lifetime_subset_complete'] is True
 assert a['trampolined_exact_wheel_root_materialization_found'] is True
 assert a['trampolined_exact_wheel_root_persistent_escape_found'] is False
 for k in ['runtime_generated_selected_wheel_pointer_stores_ruled_out','reconstructed_wheel_pointers_ruled_out','other_derived_aliases_ruled_out','stored_or_escaped_aliases_ruled_out','callbacks_and_indirect_entry_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
  assert a[k] is False
 assert a['external_provider_count']==7
