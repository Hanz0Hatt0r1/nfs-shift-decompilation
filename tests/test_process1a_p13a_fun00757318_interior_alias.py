import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/ghidra/analyze_p1a_fun00757318_interior_alias.py'
EVIDENCE = ROOT / 'evidence/p1a_p13a_fun00757318_interior_alias_closure.json'


def module():
    spec = importlib.util.spec_from_file_location('p1a_757318_alias', TOOL)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def data():
    return json.loads(EVIDENCE.read_text(encoding='utf-8'))


def test_five_exact_interior_handoffs_and_hash_locked_ranges():
    m = module()
    d = data()
    assert d['format'] == m.FORMAT and d['ready'] is True
    assert d['authority']['retail_executable_sha256'] == m.RETAIL_SHA
    assert d['authority']['upstream_contract'] == m.UPSTREAM
    assert d['scope']['derived_alias_count'] == 5
    assert [(a['site'], a['wheel_relative_offset'], a['consumer_call'], a['consumer'])
            for a in d['scope']['aliases']] == [
                (f'0x{site:08x}', f'+0x{off:x}', f'0x{call:08x}', f'FUN_{target:08x}')
                for site, off, call, target in m.ALIASES
            ]
    for name, (start, end, sha) in m.RANGES.items():
        r = d['authority']['ranges'][name]
        assert (r['start'], r['end_exclusive'], r['size'], r['sha256']) == (
            f'0x{start:08x}', f'0x{end:08x}', end-start, sha)


def test_receiver_handoff_rejects_intervening_ecx_clobber_or_call():
    m = module()
    rows = [(0x100, 'lea', 'ecx,[edi+0x610]'),
            (0x106, 'fld', 'QWORD PTR [esi+0x80]'),
            (0x10c, 'fstp', 'QWORD PTR [esp]'),
            (0x110, 'call', '0x7a06a0')]
    assert m.check_alias_to_call(rows, 0x100, 0x610, 0x110, 0x7a06a0)['intervening_instruction_count'] == 2
    with pytest.raises(AssertionError):
        m.check_alias_to_call(rows[:2] + [(0x10a, 'mov', 'ecx,eax')] + rows[2:],
                              0x100, 0x610, 0x110, 0x7a06a0)
    with pytest.raises(AssertionError):
        m.check_alias_to_call(rows[:2] + [(0x10a, 'call', '0x1234')] + rows[2:],
                              0x100, 0x610, 0x110, 0x7a06a0)


def test_interpolating_writer_rejects_pointer_store():
    m = module()
    rows = [(0x7a06b1, 'mov', 'esi,ecx'),
            (0x7a06cc, 'lea', 'ecx,[ebp+0x10]'),
            (0x7a06d2, 'call', '0x753620'),
            (0x7a06e0, 'fst', 'QWORD PTR [esi+0x20]'),
            (0x7a071f, 'lea', 'ecx,[ebp-0x10]'),
            (0x7a0777, 'call', '0x7af310')]
    rows += [(0x7a0786+i, 'fstp', f'QWORD PTR [esi+0x{off:x}]' if off else 'QWORD PTR [esi]')
             for i, off in enumerate([0, 8, 0x10, 0x18, 0, 8, 0x10, 0x18])]
    rows += [(0x7a079e, 'ret', '0x18'), (0x7a07b4, 'ret', '0x18')]
    assert m.classify_interpolating_writer(rows)['scalar_fpu_write_count'] == 9
    with pytest.raises(AssertionError):
        m.classify_interpolating_writer(rows + [(0x7a079f, 'mov', 'DWORD PTR [ebp-0x4],esi')])


def test_scalar_writer_rejects_receiver_escape():
    m = module()
    rows = [(0x7a0437, 'fstp', 'QWORD PTR [ecx]'),
            (0x7a043d, 'fstp', 'QWORD PTR [ecx+0x8]'),
            (0x7a0443, 'fst', 'QWORD PTR [ecx+0x10]'),
            (0x7a044a, 'fstp', 'QWORD PTR [ecx+0x18]'),
            (0x7a044e, 'ret', '0x18')]
    assert m.classify_scalar_writer(rows)['scalar_fpu_write_count'] == 4
    with pytest.raises(AssertionError):
        m.classify_scalar_writer(rows + [(0x7a044f, 'push', 'ecx')])


def test_only_bounded_subset_promoted():
    d = data()
    assert d['consumer_adjudication']['any_interior_alias_pointer_persisted'] is False
    assert d['consumer_adjudication']['any_interior_alias_reconstructed_as_root'] is False
    a = d['adjudication']
    assert a['p13a_fun00757318_interior_alias_subset_complete'] is True
    assert a['p13a_fun00757318_interior_alias_persistent_escape_found'] is False
    for key in ('runtime_generated_selected_wheel_pointer_stores_ruled_out',
                'reconstructed_wheel_pointers_ruled_out', 'other_derived_aliases_ruled_out',
                'stored_or_escaped_aliases_ruled_out', 'callbacks_and_indirect_entry_ruled_out',
                'p13a_slot0_complete', 'p13a_slot1_complete', 'p1_3_control_producer_complete'):
        assert a[key] is False
    assert a['external_provider_count'] == 7