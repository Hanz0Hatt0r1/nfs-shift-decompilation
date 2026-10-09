import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_slot01_receiver_loop_frontier.py'
EVIDENCE=ROOT/'evidence'/'p1a_p13a_slot01_receiver_loop_machine_closure.json'
EXPECTED=['FUN_00765c40','FUN_0075bf60','FUN_007b0710','FUN_006333f0','FUN_007b0600','FUN_00a62780','FUN_00638020','FUN_0076f030']
def load_module():
 spec=importlib.util.spec_from_file_location('p1a_receiver_loop',TOOL);assert spec and spec.loader
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_frontier_constants_and_machine_anchors_are_pinned():
 m=load_module()
 assert list(m.EXPECTED_CANDIDATES)==EXPECTED
 assert m.RETAIL_SHA256=='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
 assert m.INDEX_SHA256=='ffcee0fe527563db7b74d17533164e2256ebd5fe6296a1deef4117f80dde732e'
 assert m.EXPECTED_BYTES[0x0075BF8D]=='888c06ea000000'
 assert m.EXPECTED_BYTES[0x007B0CB9]=='b9e0b9c100'
 assert m.EXPECTED_BYTES[0x00A627D1]=='c7474000000000'
 assert m.EXPECTED_BYTES[0x0076F265]=='899ee03f0000'
 assert m.EXPECTED_REL32_TARGETS[0x0076F97F]==0x0075BF60
 assert m.EXPECTED_REL32_TARGETS[0x006332D6]==0x00638020

def test_all_eight_shallow_receiver_loop_candidates_are_rejected():
 d=json.loads(EVIDENCE.read_text())
 assert d['format']=='SHIFT.P1A.P13ASlot01ReceiverLoopMachineClosure/1'
 assert d['inventory']['candidate_functions']==EXPECTED
 assert d['inventory']['candidate_count']==8
 assert d['inventory']['verified_byte_window_count']==47
 assert d['inventory']['verified_rel32_transfer_count']==15
 assert all(x['rejected'] for x in d['candidate_adjudication'])
 assert {x['function'] for x in d['candidate_adjudication']}==set(EXPECTED)

def test_bounded_subset_closes_but_slot_and_p13_gates_stay_fail_closed():
 a=json.loads(EVIDENCE.read_text())['adjudication']
 assert a['shallow_receiver_loop_depth4_surface_complete'] is True
 assert a['shallow_receiver_loop_candidate_count']==8
 assert a['shallow_receiver_loop_rejected_count']==8
 assert a['shallow_receiver_loop_selected_hdvehicle_writer_found'] is False
 assert a['all_ordinary_mov_unrolled_custom_copy_init_ruled_out'] is False
 assert a['indirect_copy_dispatch_ruled_out'] is False
 assert a['deeper_direct_copy_init_paths_ruled_out'] is False
 assert a['slot0_selected_root_alias_callee_bulk_copy_complete'] is False
 assert a['slot1_selected_root_alias_callee_bulk_copy_complete'] is False
 assert a['p1_3_control_producer_complete'] is False
 assert a['external_provider_count']==7

def test_alias_kill_and_exact_receiver_domains_are_explicit():
 d=json.loads(EVIDENCE.read_text())
 by={x['function']:x for x in d['candidate_adjudication']}
 assert 'killed-alias false positive' in ' '.join(by['FUN_00a62780']['evidence'])
 assert '0x00c1b9e0' in ' '.join(by['FUN_007b0600']['evidence'])
 assert 'HDVehicle+0xea..+0xf9' in ' '.join(by['FUN_0075bf60']['evidence'])
 assert 'HDVehicle+0x3fe0' in ' '.join(by['FUN_0076f030']['evidence'])
