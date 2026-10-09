import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'verify_p1a_slot01_x87_pointer_chain_closure.py'
EVIDENCE=ROOT/'evidence'/'p1a_p13a_slot01_x87_pointer_chain_closure.json'
RESOLVED=['FUN_0075c0d0','FUN_007b8630','FUN_0075ada0','FUN_007b7840']

def load_tool():
    spec=importlib.util.spec_from_file_location('x87_pointer_chain',TOOL); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def load_evidence(): return json.loads(EVIDENCE.read_text(encoding='utf-8'))

def test_machine_anchors_and_candidate_set_are_pinned():
    m=load_tool(); assert m.RESOLVED==RESOLVED
    assert m.EXPECTED[0x00771231]=='push 0x0'
    assert m.EXPECTED[0x007B19D9]=='call 0x75c0d0'
    assert m.EXPECTED[0x0076DF76]=='push 0x60'
    assert m.EXPECTED[0x007B309D]=='mov DWORD PTR [esi],0xb0cd90'
    assert m.EXPECTED[0x0076DFA0]=='mov DWORD PTR [esi+0x339c],eax'
    assert m.EXPECTED[0x007B82F4]=='call 0x7b7840'

def test_four_remaining_candidates_close_negative():
    d=load_evidence(); assert d['format']=='SHIFT.P1A.P13ASlot01X87PointerChainClosure/1'
    assert d['frontier']=={'candidate_count':18,'resolved_before':14,'resolved_in_tranche':4,'resolved_total':18,'remaining_count':0}
    assert [r['function'] for r in d['resolved']]==RESOLVED
    assert all(r['rejected'] for r in d['resolved'])

def test_heap_object_identity_is_exact():
    p=load_evidence()['object_provenance']
    assert p=={'allocation_size':'0x60','allocation_site':'FUN_0076df50','constructor':'FUN_007b3070','exact_vptr':'0x00b0cd90','owner_field':'HDVehicle+0x339c'}

def test_x87_closes_while_later_frontiers_remain_fail_closed():
    a=load_evidence()['adjudication']
    assert a['x87_zero_init_semantics_complete'] is True
    assert a['x87_remaining_count']==0 and a['x87_resolved_total']==18
    assert a['x87_selected_hdvehicle_target_writer_found'] is False
    assert a['sse_vector_copy_init_complete'] is False
    assert a['deeper_direct_aliases_ruled_out'] is False
    assert a['indirect_callback_aliases_ruled_out'] is False
    assert a['p13a_slot0_complete'] is False and a['p13a_slot1_complete'] is False
    assert a['p1_3_control_producer_complete'] is False
    assert a['external_provider_count']==7
