import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_writer_singleton_direct_propagation.json'
def data():return json.loads(EV.read_text())
def test_contract_identity():
 r=data();assert r['format']=='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94WriterSingletonDirectPropagation/1';assert r['ready'] is True
def test_reference_and_load_counts():
 p=data()['proof'];assert p['decoded_instruction_count']==2847850;assert p['singleton_direct_reference_count']==115;assert p['singleton_direct_load_count']==113
def test_same_block_stores():
 p=data()['proof'];assert p['same_block_stack_store_count']==4;assert p['same_block_stack_store_sites']==['0x0057b6e4','0x00d77fad','0x00d77fb0','0x00d77fb3'];assert p['same_block_nonstack_store_count']==0
def test_call_frontier_counts():
 p=data()['proof'];assert p['same_block_ecx_receiver_call_count']==30;assert p['same_block_edx_argument_call_count']==2
def test_bounded_negative_promoted_only():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_d94_writer_singleton_direct_propagation_subset_complete'] is True;assert a['writable_callback_pair_d94_writer_singleton_same_block_nonstack_store_found'] is False;assert a['writable_callback_pair_d94_writer_singleton_direct_store_into_loop_source_record_found'] is False;assert a['writable_callback_pair_d94_writer_consumer_receiver_identity_proven'] is False;assert a['writable_callback_pair_d94_runtime_writer_relevant_to_loop_bound_proven'] is False
def test_aggregate_gates_fail_closed():
 a=data()['adjudication'];assert a['writable_callback_pair_d94_value_range_proven'] is False;assert a['p13a_slot0_complete'] is False;assert a['p13a_slot1_complete'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['callbacks_and_indirect_entry_ruled_out'] is False;assert a['external_provider_count']==7
