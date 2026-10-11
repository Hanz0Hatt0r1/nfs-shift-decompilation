import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_entry_slot0_contract.json'
def data(): return json.loads(EV.read_text())
def test_contract_identity():
 r=data(); assert r['format']=='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94EntrySlot0Contract/1'; assert r['ready'] is True
def test_entry_class_exact():
 p=data()['proof']; assert p['entry_allocation_size']=='0x68'; assert p['entry_constructor']=='0x008309f0'; assert p['entry_vtable']=='0x00b17fe0'; assert p['entry_vtable_slot0_target']=='0x00835290'
def test_consumer_call_shape():
 p=data()['proof']; assert p['lookup_target']=='0x0082da60'; assert p['consumer_call_site']=='0x0045ecca'; assert p['consumer_destination']=='[esi+0xd94]'; assert p['consumer_entry_arg']=='&[esi+0xcb0]'; assert p['consumer_stack_args']==[0,0]
def test_slot0_return_shape():
 p=data()['proof']; assert p['slot0_embedded_container']=='this+0x40'; assert p['slot0_container_acquire']=='0x0062f6f0'; assert p['slot0_finalize']=='0x008339e0'; assert p['slot0_zero_return_possible'] is True; assert p['slot0_nonzero_return_is_container_derived'] is True
def test_target_promoted_but_range_not_promoted():
 a=data()['adjudication']; assert a['p13a_fun005ffc50_writable_callback_pair_d94_entry_slot0_contract_subset_complete'] is True; assert a['writable_callback_pair_d94_entry_slot0_concrete_target_proven'] is True; assert a['writable_callback_pair_d94_entry_slot0_target']=='0x00835290'; assert a['writable_callback_pair_d94_entry_slot0_nonzero_return_domain_bounded'] is False; assert a['writable_callback_pair_d94_value_range_proven'] is False
def test_aggregate_gates_fail_closed():
 a=data()['adjudication']; assert a['p13a_slot0_complete'] is False; assert a['p13a_slot1_complete'] is False; assert a['p1_3_control_producer_complete'] is False; assert a['callbacks_and_indirect_entry_ruled_out'] is False; assert a['external_provider_count']==7
