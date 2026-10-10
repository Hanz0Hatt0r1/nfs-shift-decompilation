import json
from pathlib import Path

EVIDENCE=Path('evidence/p1b_hdvehicle_4330_nonthread_callback_tranche1.json')

def load():
    return json.loads(EVIDENCE.read_text(encoding='utf-8'))

def test_partition_and_callbacks():
    d=load(); s=d['surface']
    assert s['frontier_callsite_count']==11
    assert s['resolved_callsite_count']==7
    assert s['remaining_callsite_count']==4
    got={(r['name'],r['address']) for r in s['resolved_callbacks']}
    assert got=={
        ('FUN_00634870','0x00634870'),
        ('lpCompletionRoutine_006553e0','0x006553e0'),
        ('lpCompletionRoutine_00655410','0x00655410'),
    }
    assert s['remaining_apis']==['SetWaitableTimer','WSARecv','WSARecvFrom']

def test_fail_closed_gates():
    a=load()['adjudication']
    assert a['wndproc_registration_subset_complete'] is True
    assert a['readfileex_writefileex_completion_subset_complete'] is True
    assert a['exact_4330_carrier_callback_found'] is False
    assert a['nonthread_callback_argument_provenance_complete'] is False
    assert a['runtime_callback_registration_ruled_out'] is False
    assert a['indirect_entry_into_carriers_ruled_out'] is False
    assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
    assert a['last_literal_0x004b86cf_rejected'] is False
    assert a['p1_3_control_producer_complete'] is False
    assert a['external_provider_count']==7
