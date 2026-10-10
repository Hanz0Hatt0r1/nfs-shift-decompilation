import json
from pathlib import Path

EVIDENCE=Path('evidence/p1b_hdvehicle_4330_nonthread_callback_tranche2.json')

def load():
    return json.loads(EVIDENCE.read_text(encoding='utf-8'))

def test_three_null_callbacks_leave_one_site():
    d=load(); s=d['surface']
    assert s['resolved_callsite_count']==3
    assert s['remaining_callsite_count']==1
    assert {(r['api'],r['callsite'],r['callback']) for r in s['resolved_sites']}=={
        ('SetWaitableTimer','0x0099882b','NULL'),
        ('SetWaitableTimer','0x00998e13','NULL'),
        ('WSARecv','0x005fdd21','NULL'),
    }
    assert s['remaining_site']=={'api':'WSARecvFrom','callsite':'0x005fdd09'}

def test_fail_closed_global_gates():
    a=load()['adjudication']
    assert a['setwaitabletimer_completion_subset_complete'] is True
    assert a['wsarecv_completion_subset_complete'] is True
    assert a['nonthread_callback_argument_provenance_complete'] is False
    assert a['runtime_callback_registration_ruled_out'] is False
    assert a['indirect_entry_into_carriers_ruled_out'] is False
    assert a['manager_374_join_to_hdvehicle_4330_complete'] is False
    assert a['last_literal_0x004b86cf_rejected'] is False
    assert a['p1_3_control_producer_complete'] is False
    assert a['external_provider_count']==7
