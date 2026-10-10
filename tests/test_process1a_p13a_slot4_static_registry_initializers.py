import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_slot4_static_registry_initializers.py'
EVIDENCE=ROOT/'evidence'/'p1a_p13a_slot4_static_registry_initializers.json'

def module():
    spec=importlib.util.spec_from_file_location('p1a_slot4_static',TOOL)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def data():return json.loads(EVIDENCE.read_text(encoding='utf-8'))

def test_static_registry_exact_rows_and_vptrs():
    p=data();assert p['format']=='SHIFT.P1A.P13ASlot4StaticRegistryInitializers/1'
    assert p['static_registration_count']==2
    assert [(r['registration_call'],r['registered_table'],r['initializer'],r['returned_object_vptr_on_success']) for r in p['static_initializer_rows']]==[
        ('0x005ff8c6','0x00ae7d84','0x00614700','0x00ae7d84'),
        ('0x005ff8d5','0x00ae7d6c','0x00614130','0x00ae7d6c')]
    assert all(r['returned_object_vptr_is_animation_vptr'] is False for r in p['static_initializer_rows'])
    assert p['static_initializer_rows'][1]['returned_object_can_be_null'] is True

def test_callback_result_not_registration_pointer():
    r=data()['registry_initializer_result_path']
    assert r['callback_table_entry_offset']=='+0x0'
    assert r['result_storage_offset']=='record+0x8'
    assert r['result_used_by_slot4_dispatch']=='0x006145c4'
    assert r['static_result_types_exclude_animation_vtable'] is True
    assert r['dynamic_registration_forwarder']=='0x005ffc7a'
    assert r['dynamic_result_types_closed'] is False

def test_machine_range_sha_and_exact_anchors():
    p=data();m=module()
    assert p['authority']['retail_executable_sha256']==m.SHA
    assert p['authority']['upstream_contract']==m.UPSTREAM
    for name,(start,end,section,expected_hash) in m.RANGES.items():
        x=p['authority']['machine_ranges'][name]
        assert x['start']==f'0x{start:08x}' and x['end_exclusive']==f'0x{end:08x}'
        assert x['size']==end-start and x['sha256']==expected_hash and len(x['sha256'])==64
    a=p['machine_anchors']
    assert a['initializer_A_vptr_store']=='0x0061472b mov DWORD PTR [eax],0xae7d84'
    assert a['initializer_B_vptr_store']=='0x00614170 mov DWORD PTR [eax],0xae7d6c'
    assert a['init_save_result']=='0x0061458b mov DWORD PTR [edi+0x8],eax'

def test_narrow_gate_and_dynamic_path_fail_closed():
    a=data()['adjudication']
    assert a['p13a_slot4_static_registry_initializer_result_subset_complete'] is True
    assert a['p13a_slot4_two_static_registration_results_are_animation_object'] is False
    for k in ['fun0067b660_callback_argument_provenance_complete','fun0067b660_callback_argument_is_selected_wheel_ruled_out','callbacks_and_indirect_entry_ruled_out','runtime_generated_selected_wheel_pointer_stores_ruled_out','stored_or_escaped_aliases_ruled_out','p13a_slot0_complete','p13a_slot1_complete','p1_3_control_producer_complete']:
        assert a[k] is False
    assert a['external_provider_count']==7