import json
from pathlib import Path

EVIDENCE=Path('evidence/p1b_hdvehicle_4330_nonthread_callback_frontier.json')

def test_nonthread_callback_frontier_is_pinned_and_fail_closed():
    data=json.loads(EVIDENCE.read_text(encoding='utf-8'))
    assert data['format']=='SHIFT.P1B.HDVehicle4330NonThreadCallbackFrontier/1'
    surf=data['api_surface']
    assert surf['direct_callsite_count']==11
    assert surf['exact_carrier_caller_count']==0
    counts={name:0 for name in surf['families']}
    for row in surf['rows']:
        assert row['direct'] is True
        counts[row['api']]+=1
    assert counts=={
        'RegisterClassExW':3,'RegisterClassA':0,'SetWaitableTimer':2,
        'ReadFileEx':2,'WriteFileEx':2,'WSARecv':1,'WSARecvFrom':1,
    }
    adj=data['adjudication']
    assert adj['nonthread_callback_api_callsite_inventory_complete'] is True
    assert adj['callback_argument_provenance_complete'] is False
    assert adj['runtime_callback_registration_ruled_out'] is False
    assert adj['indirect_entry_into_carriers_ruled_out'] is False
    assert adj['manager_374_join_to_hdvehicle_4330_complete'] is False
    assert adj['last_literal_0x004b86cf_rejected'] is False
    assert adj['p1_3_control_producer_complete'] is False
    assert adj['external_provider_count']==7

def test_expected_callsites_are_exact():
    data=json.loads(EVIDENCE.read_text(encoding='utf-8'))
    got={(r['api'],r['callsite']) for r in data['api_surface']['rows']}
    expected={
      ('RegisterClassExW','0x00634b89'),('RegisterClassExW','0x00634c52'),('RegisterClassExW','0x00634c93'),
      ('SetWaitableTimer','0x0099882b'),('SetWaitableTimer','0x00998e13'),
      ('ReadFileEx','0x006558d5'),('ReadFileEx','0x00655c15'),
      ('WriteFileEx','0x006559df'),('WriteFileEx','0x00655dca'),
      ('WSARecv','0x005fdd21'),('WSARecvFrom','0x005fdd09'),
    }
    assert got==expected
