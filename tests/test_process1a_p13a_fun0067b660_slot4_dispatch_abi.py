import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'ghidra' / 'analyze_p1a_fun0067b660_slot4_dispatch_abi.py'
EVIDENCE = ROOT / 'evidence' / 'p1a_p13a_fun0067b660_slot4_dispatch_abi_frontier.json'


def module():
    spec = importlib.util.spec_from_file_location('p1a_slot4_abi', TOOL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def data():
    return json.loads(EVIDENCE.read_text(encoding='utf-8'))


def test_retail_slot4_inventory_and_candidate_addresses():
    p = data()
    assert p['format'] == 'SHIFT.P1A.P13AFun0067b660Slot4DispatchAbiFrontier/1'
    i = p['slot4_abi_inventory']
    assert i['decoded_instruction_count'] == 2847850
    assert i['raw_memory_slot4_call_count'] == 79
    assert i['near_register_slot4_call_count'] == 1832
    assert i['raw_memory_slot4_immediate_cleanup'] == []
    assert [(x['call'], x['slot4_load'], x['caller_cleanup'])
            for x in i['near_register_slot4_immediate_cleanup']] == [
        ('0x006022ee', '0x006022ea', '0x006022f0'),
        ('0x006145c4', '0x006145c0', '0x006145c6'),
    ]


def test_registry_provenance_does_not_assume_derived_animation_target():
    p = data()
    r = p['registry_path']
    assert r['direct_registration_calls'] == [
        '0x005ff8c6', '0x005ff8d5', '0x005ffc7a']
    assert r['array_record_stride'] == 12 and r['array_capacity'] == 8
    assert r['callback_result_field'] == 'record+0x8'
    assert r['record_8_populated_by_callback_result'] is True
    assert r['pushed_argument_equals_registry_receiver'] is True
    assert r['registered_fun0067b660_object_proven'] is False
    assert r['registry_dispatch_target_fun0067b660_proven'] is False
    assert p['secondary_path']['pushed_argument_is_loaded_vtable_pointer'] is True
    assert p['secondary_path']['target_fun0067b660_proven'] is False


def test_machine_ranges_and_anchor_constants_are_reproducible():
    p = data()
    mod = module()
    assert p['authority']['retail_executable_sha256'] == mod.RETAIL_SHA
    assert p['authority']['upstream_contract'] == mod.UPSTREAM
    for name, (start, end, expected_hash) in mod.RANGES.items():
        item = p['authority']['machine_ranges'][name]
        assert item['start'] == f'0x{start:08x}'
        assert item['end_exclusive'] == f'0x{end:08x}'
        assert item['size'] == end - start
        assert item['sha256'] == expected_hash and len(item['sha256']) == 64
    a = p['machine_anchors']
    assert a['registry_result_store'] == '0x0061458b mov DWORD PTR [edi+0x8],eax'
    assert a['registry_arg'] == '0x006145c3 push eax'
    assert a['registry_cleanup'] == '0x006145c6 add esp,0x4'
    assert a['secondary_arg'] == '0x006022ed push eax'
    assert a['secondary_cleanup'] == '0x006022f0 add esp,0x4'


def test_streaming_scanner_enforces_call_clobber_and_immediate_cleanup():
    m = module()
    fixture = [
        (0x1000, 'mov', 'edx,DWORD PTR [ecx+0x4]'),
        (0x1003, 'push', 'eax'),
        (0x1004, 'call', 'edx'),
        (0x1006, 'add', 'esp,0x4'),
        (0x1009, 'mov', 'edx,DWORD PTR [ecx+0x4]'),
        (0x100c, 'call', '0x1234'),
        (0x1011, 'push', 'eax'),
        (0x1012, 'call', 'edx'),
        (0x1014, 'add', 'esp,0x4'),
        (0x1017, 'mov', 'edx,DWORD PTR [ecx+0x4]'),
        (0x101a, 'mov', 'edx,0x42'),
        (0x101f, 'push', 'eax'),
        (0x1020, 'call', 'edx'),
        (0x1022, 'add', 'esp,0x4'),
        (0x1025, 'mov', 'edx,DWORD PTR [ecx+0x4]'),
        (0x1028, 'push', 'eax'),
        (0x1029, 'call', 'edx'),
        (0x102b, 'add', 'esp,0x8'),
        (0x102e, 'push', 'eax'),
        (0x102f, 'call', 'DWORD PTR [edx+0x4]'),
        (0x1032, 'add', 'esp,0x4'),
    ]
    result = m.scan(fixture)
    assert result['near_register_slot4_call_count'] == 2
    assert [x['call'] for x in result['near_register_slot4_immediate_cleanup']] == ['0x00001004']
    assert [x['call'] for x in result['raw_memory_slot4_immediate_cleanup']] == ['0x0000102f']


def test_only_narrow_gate_is_promoted():
    a = data()['adjudication']
    assert a['p13a_fun0067b660_immediate_slot4_caller_cleanup_subset_complete'] is True
    for key in (
        'fun0067b660_immediate_slot4_dispatch_target_proven',
        'fun0067b660_callback_argument_provenance_complete',
        'fun0067b660_callback_argument_is_selected_wheel_ruled_out',
        'callbacks_and_indirect_entry_ruled_out',
        'runtime_generated_selected_wheel_pointer_stores_ruled_out',
        'stored_or_escaped_aliases_ruled_out',
        'p13a_slot0_complete', 'p13a_slot1_complete', 'p1_3_control_producer_complete',
    ):
        assert a[key] is False
    assert a['external_provider_count'] == 7