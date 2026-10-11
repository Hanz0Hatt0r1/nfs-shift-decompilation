import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EV=ROOT/'evidence'/'p1a_p13a_fun005ffc50_writable_callback_pair_d94_loop_source_key_semantics.json'
def data():return json.loads(EV.read_text())
def test_contract_identity():
 r=data();assert r['format']=='SHIFT.P1A.P13AFun005ffc50WritableCallbackPairD94LoopSourceKeySemantics/1';assert r['ready'] is True
def test_key_comparison_sites():
 p=data()['proof'];assert p['source_record_key_load_site']=='0x005033f1';assert p['source_record_key_null_guard_site']=='0x005033f3';assert p['comparison_call_site']=='0x005033fd';assert p['comparison_target']=='0x00901179'
def test_empty_key_fallback():
 p=data()['proof'];assert p['empty_key_fallback']=='0x00aa9b60';assert p['empty_key_fallback_first_dword']==0
def test_case_insensitive_nul_semantics():
 p=data()['proof'];assert p['default_ascii_compare_target']=='0x00901071';assert p['default_compare_ascii_uppercase_range']==['0x41','0x5a'];assert p['default_compare_ascii_fold_delta']=='0x20';assert p['default_compare_terminates_on_nul'] is True;assert p['non_null_source_record_dword0_is_string_key_input'] is True
def test_semantics_promoted_but_identity_open():
 a=data()['adjudication'];assert a['p13a_fun005ffc50_writable_callback_pair_d94_loop_source_key_semantics_subset_complete'] is True;assert a['writable_callback_pair_d94_loop_source_record_dword0_string_key_compatible'] is True;assert a['writable_callback_pair_d94_loop_source_record_dword0_unique_type_proven'] is False;assert a['writable_callback_pair_d94_writer_consumer_receiver_identity_proven'] is False;assert a['writable_callback_pair_d94_runtime_writer_relevant_to_loop_bound_proven'] is False
def test_aggregate_gates_fail_closed():
 a=data()['adjudication'];assert a['writable_callback_pair_d94_value_range_proven'] is False;assert a['p13a_slot0_complete'] is False;assert a['p13a_slot1_complete'] is False;assert a['p1_3_control_producer_complete'] is False;assert a['callbacks_and_indirect_entry_ruled_out'] is False;assert a['external_provider_count']==7
