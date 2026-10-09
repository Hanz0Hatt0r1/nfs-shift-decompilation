import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1a_slot01_unrolled_mov_copy_closure.py'
EVIDENCE=ROOT/'evidence'/'p1a_p13a_slot01_unrolled_mov_copy_machine_closure.json'
EXPECTED=['FUN_0076e560','FUN_007b0710','FUN_00403d00','FUN_004e9380','FUN_00633290','FUN_006333f0','FUN_0075a8d0','FUN_007b0580','FUN_0064fef0','FUN_007b0450','_LocaleUpdate']
def module():
 s=importlib.util.spec_from_file_location('closure',TOOL);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_verifier_pins_candidate_set_and_machine_anchors():
 m=module(); assert m.EXPECTED_CANDIDATES==EXPECTED
 assert m.RETAIL_SHA256=='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
 assert len(m.EXPECTED_BYTES)==76
 assert len(m.EXPECTED_CALL_TARGETS)==16
 assert m.EXPECTED_BYTES[0x00767CBC]=='8dbec8400000'
 assert m.EXPECTED_BYTES[0x007B0CF4]=='b9e0b9c100'
 assert m.EXPECTED_CALL_TARGETS[0x007B0C8E]==0x0074F560
 assert m.EXPECTED_CALL_TARGETS[0x00767CD3]==0x0075A8D0

def test_all_eleven_frontier_candidates_are_semantically_rejected():
 d=json.loads(EVIDENCE.read_text())
 assert d['format']=='SHIFT.P1A.P13ASlot01UnrolledMovCopyMachineClosure/1'
 assert d['inventory']['candidate_functions']==EXPECTED
 assert d['inventory']['candidate_count']==11
 assert d['inventory']['verified_byte_window_count']==76
 assert d['inventory']['verified_rel32_transfer_count']==16
 assert all(x['rejected'] for x in d['candidate_adjudication'])
 assert {x['function'] for x in d['candidate_adjudication']}==set(EXPECTED)

def test_key_destination_domains_are_explicit():
 d=json.loads(EVIDENCE.read_text()); by={x['function']:x for x in d['candidate_adjudication']}
 assert '0x00c1bae0' in ' '.join(by['FUN_007b0710']['evidence'])
 assert 'HDVehicle+0x40c8..+0x40d7' in ' '.join(by['FUN_0075a8d0']['evidence'])
 assert 'stack-local output structure' in ' '.join(by['FUN_007b0580']['evidence'])
 assert 'cannot execute' in ' '.join(by['FUN_007b0450']['evidence'])
 assert 'CRT formatting path' in ' '.join(by['_LocaleUpdate']['evidence'])

def test_only_bounded_unrolled_copy_subset_closes():
 a=json.loads(EVIDENCE.read_text())['adjudication']
 assert a['shallow_unrolled_mov_copy_semantics_complete'] is True
 assert a['shallow_unrolled_mov_copy_candidate_count']==11
 assert a['shallow_unrolled_mov_copy_rejected_count']==11
 assert a['shallow_unrolled_mov_copy_selected_hdvehicle_slot_writer_found'] is False
 assert a['straight_line_zero_init_complete'] is False
 assert a['sse_vector_custom_copy_complete'] is False
 assert a['deeper_direct_alias_paths_complete'] is False
 assert a['indirect_callback_alias_paths_complete'] is False
 assert a['slot0_selected_root_alias_callee_bulk_copy_complete'] is False
 assert a['slot1_selected_root_alias_callee_bulk_copy_complete'] is False
 assert a['p1_3_control_producer_complete'] is False
 assert a['external_provider_count']==7
