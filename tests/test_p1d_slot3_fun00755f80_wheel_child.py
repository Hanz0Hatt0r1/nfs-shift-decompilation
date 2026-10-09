import importlib.util, json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1d_slot3_fun00755f80_wheel_child_pe.py'
EVIDENCE=ROOT/'evidence'/'p1d_slot3_fun00755f80_wheel_child_closure.json'
UPSTREAM=ROOT/'evidence'/'p1a_p13a_slot01_x87_reuse_tranche_closure.json'

def load_module():
    spec=importlib.util.spec_from_file_location('p1d_755f80',TOOL); assert spec and spec.loader
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_upstream_hdvehicle_identity_required():
    m=load_module(); p=m.load_upstream(UPSTREAM)
    row=next(r for r in p['resolved'] if r['function']=='FUN_00763570')
    assert row['domain']=='HDVehicle root'

def test_upstream_drift_fails_closed(tmp_path):
    m=load_module(); p=json.loads(UPSTREAM.read_text())
    next(r for r in p['resolved'] if r['function']=='FUN_00763570')['domain']='unknown'
    f=tmp_path/'bad.json'; f.write_text(json.dumps(p))
    with pytest.raises(ValueError): m.load_upstream(f)

def test_pinned_path_is_child_only_after_wheel_deref():
    d=json.loads(EVIDENCE.read_text())
    assert d['format']=='SHIFT.P1D.Slot3Fun00755f80WheelChildClosure/1'
    assert d['caller']['wheel_seed']=='HDVehicle+0x400'
    assert d['caller']['stride']=='0xa80'
    assert d['caller']['slot3_receiver']=='HDVehicle+0x2380'
    c=d['callee']
    assert c['wheel_root_write_count']==0
    assert c['child_pointer_source']=='[wheel+0x420]'
    assert c['child_write_offsets']==['+0x48','+0x50','+0x58']
    assert c['exact_wheel_root_forwarded_to_direct_callee'] is False
    assert c['indirect_call_count']==0
    assert c['target_overlap'] is False

def test_gates_remain_fail_closed():
    a=json.loads(EVIDENCE.read_text())['adjudication']
    assert a['slot3_fun00763570_to_fun00755f80_exact_wheel_path_complete'] is True
    assert a['fun00755f80_selected_target_writer_found'] is False
    assert a['fun00755f80_exact_wheel_escape_found'] is False
    assert a['deeper_direct_aliases_ruled_out'] is False
    assert a['indirect_callback_aliases_ruled_out'] is False
    assert a['slot3_writer_provenance_proven'] is False
    assert a['p1_3d_complete'] is False
    assert a['external_provider_count']==7
