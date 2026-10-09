import json
from pathlib import Path

EVIDENCE=Path('evidence/p1d_controller1_loader_reachability.json')

def test_pinned_loader_surface_stays_fail_closed():
    p=json.loads(EVIDENCE.read_text(encoding='utf-8'))
    assert p['format']=='SHIFT.P1D.Controller1LoaderReachability/1'
    assert p['counts']['direct_loader_call_count']==37
    assert p['counts']['direct_worker_reachable_loader_call_count']==7
    assert p['counts']['reachable_by_target']=={'GetModuleHandleA':6,'LoadLibraryA':1}
    assert {r['caller'] for r in p['reachable_calls']}=={'0x0090748b','0x0090a9bb','0x0090aa27','0x0090aa9e','0x0090abb8','0x009189cd','0x0091c073'}
    a=p['adjudication']
    assert a['direct_loader_surface_bounded'] is True
    assert a['reachable_loader_surface_adds_new_apc_resolution_candidate'] is False
    assert a['manual_or_hashed_resolution_ruled_out'] is False
    assert a['native_or_syscall_apc_injection_ruled_out'] is False
    assert a['controller1_timing_exhaustive'] is False
    assert a['p1_3d_complete'] is False
    assert a['external_provider_count']==7

def test_reachable_contexts_are_known_non_apc_families():
    p=json.loads(EVIDENCE.read_text(encoding='utf-8'))
    strings={s for r in p['reachable_calls'] for s in r['local_strings']}
    assert 'KERNEL32.DLL' in strings and 'USER32.DLL' in strings and 'mscoree.dll' in strings
    assert 'NtQueueApcThread' not in strings and 'QueueUserAPC' not in strings
