import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'verify_p1a_slot01_x87_reuse_tranche.py'
EVIDENCE=ROOT/'evidence'/'p1a_p13a_slot01_x87_reuse_tranche_closure.json'
RESOLVED={'FUN_00763570','FUN_00770e80','FUN_00755a60','FUN_00760b50','FUN_0076e560','FUN_00647a10','FUN_0070fae0','FUN_0076f030','FUN_0088f110'}
REMAINING={'FUN_00766510','FUN_0075c0d0','FUN_007aa940','FUN_007b8630','FUN_0075ada0','FUN_0075afc0','FUN_007876e0','FUN_007ade70','FUN_007b7840'}
def load_tool():
    spec=importlib.util.spec_from_file_location('x87_tranche',TOOL); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def test_verifier_pins_representative_machine_sites():
    m=load_tool(); assert m.RETAIL_SHA256=='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
    assert set(m.EXPECTED_SITES)==RESOLVED
    assert m.EXPECTED_SITES['FUN_00755a60'][0x00755E2E]=='fstp QWORD PTR [esi+0x850]'
    assert m.EXPECTED_SITES['FUN_0076f030'][0x0076F03D]=='fst QWORD PTR [esi+0x18]'
    assert set(m.REMAINING)==REMAINING
def test_evidence_closes_exactly_first_nine_candidates():
    d=json.loads(EVIDENCE.read_text())
    assert d['format']=='SHIFT.P1A.P13ASlot01X87ReuseTrancheClosure/1'
    assert d['frontier']=={'candidate_count':18,'resolved_in_tranche':9,'remaining_count':9}
    assert {r['function'] for r in d['resolved']}==RESOLVED
    assert all(r['rejected'] for r in d['resolved'])
    assert set(d['remaining_candidates'])==REMAINING
def test_global_gates_remain_fail_closed():
    a=json.loads(EVIDENCE.read_text())['adjudication']
    assert a['x87_reuse_tranche_complete'] is True
    assert a['x87_reuse_tranche_rejected_count']==9
    assert a['x87_selected_hdvehicle_target_writer_found_in_tranche'] is False
    assert a['x87_zero_init_semantics_complete'] is False
    assert a['sse_vector_copy_init_complete'] is False
    assert a['p13a_slot0_complete'] is False and a['p13a_slot1_complete'] is False
    assert a['p1_3_control_producer_complete'] is False and a['external_provider_count']==7
