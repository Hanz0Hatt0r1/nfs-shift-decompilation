import importlib.util, json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'build_p1d_slot3_fun00766510_exact_root_handoff.py'
IDENTITY=ROOT/'evidence'/'p1a_p13a_slot01_x87_stack_output_tranche_closure.json'
TAIL=ROOT/'evidence'/'fun_00766510_residual_tail_closure.json'
EVIDENCE=ROOT/'evidence'/'p1d_slot3_fun00766510_exact_root_handoff.json'

def load_module():
    spec=importlib.util.spec_from_file_location('p1d_766510_handoff',TOOL); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_builder_reproduces_pinned_handoff():
    m=load_module(); got=m.build(IDENTITY,TAIL); expected=json.loads(EVIDENCE.read_text())
    assert got==expected

def test_identity_drift_fails_closed(tmp_path):
    m=load_module(); p=json.loads(IDENTITY.read_text())
    next(r for r in p['resolved'] if r['function']=='FUN_00766510')['domain']='unknown'
    f=tmp_path/'bad.json'; f.write_text(json.dumps(p))
    with pytest.raises(ValueError): m.build(f,TAIL)

def test_exact_calls_and_effect_are_disjoint_from_slot3():
    d=json.loads(EVIDENCE.read_text())
    assert [x['callsite'] for x in d['exact_root_calls']]==['0x00766da5','0x00766dba']
    assert all(x['receiver']=='HDVehicle' for x in d['exact_root_calls'])
    assert d['callee_effect']['proven_hdvehicle_write_offsets']==['+0x40a0','+0x40a8','+0x40b0']
    assert d['callee_effect']['selected_target_overlap'] is False

def test_global_alias_gates_remain_open():
    a=json.loads(EVIDENCE.read_text())['adjudication']
    assert a['slot3_fun00766510_fun00758fc0_exact_root_pair_complete'] is True
    assert a['fun00758fc0_selected_slot3_writer_found'] is False
    assert a['deeper_direct_aliases_ruled_out'] is False
    assert a['indirect_callback_aliases_ruled_out'] is False
    assert a['slot3_writer_provenance_proven'] is False
    assert a['p1_3d_complete'] is False
    assert a['external_provider_count']==7
