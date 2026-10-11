import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_entry_payload_address.json'
def data(): return json.loads(EV.read_text())
def test_contract_identity():
 r=data(); assert r['format']=='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94EntryPayloadAddress/1'; assert r['ready'] is True
def test_allocator_formula():
 p=data()['proof']; assert p['allocator_slot_formula']=='payload_base + index * stride'; assert p['block_payload_base_field']=='block+0x4'; assert p['slot_allocator']=='0x0063ac90'
def test_container_configuration():
 p=data()['proof']; assert p['entry_container']=='entry+0x40'; assert p['container_init_call']=='0x00830d05'; assert p['container_init_flags']==4; assert p['container_block_quantity_argument']=='0x80'; assert p['container_edx_argument']=='0x100'
def test_nonzero_return_is_address():
 p=data()['proof']; assert p['slot0_container_acquire']=='0x0062f6f0'; assert p['nonzero_slot0_return_is_payload_address'] is True
def test_receiver_identity_stays_open():
 a=data()['adjudication']; assert a['p13a_fun005ffc50_writable_callback_pair_d94_entry_payload_address_subset_complete'] is True; assert a['writable_callback_pair_d94_entry_slot0_nonzero_return_is_payload_address'] is True; assert a['writable_callback_pair_d94_writer_consumer_receiver_identity_proven'] is False; assert a['writable_callback_pair_d94_value_range_proven'] is False
def test_aggregate_gates_fail_closed():
 a=data()['adjudication']; assert a['p13a_slot0_complete'] is False; assert a['p13a_slot1_complete'] is False; assert a['p1_3_control_producer_complete'] is False; assert a['callbacks_and_indirect_entry_ruled_out'] is False; assert a['external_provider_count']==7
