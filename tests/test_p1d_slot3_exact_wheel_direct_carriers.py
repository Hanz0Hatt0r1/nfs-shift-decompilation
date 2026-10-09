import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools'/'ghidra'/'analyze_p1d_slot3_exact_wheel_direct_carriers_pe.py'
EVIDENCE=ROOT/'evidence'/'p1d_slot3_exact_wheel_direct_carrier_closure.json'
UPSTREAM=ROOT/'evidence'/'p1a_p13a_slot01_x87_reuse_tranche_closure.json'

def load_module():
    spec=importlib.util.spec_from_file_location('p1d_slot3_carriers',TOOL); assert spec and spec.loader
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def test_upstream_identity_contract_is_exact():
    m=load_module(); p=m.load_upstream(UPSTREAM)
    rows={r['function']:r for r in p['resolved']}
    assert rows['FUN_00770e80']['domain']=='HDVehicle root'
    assert rows['FUN_00755a60']['domain']=='wheel receiver HDVehicle+0x400+slot*0xa80'
    assert rows['FUN_00760b50']['domain']=='wheel receiver HDVehicle+0x400+slot*0xa80'

def test_upstream_identity_drift_fails_closed(tmp_path):
    m=load_module(); p=json.loads(UPSTREAM.read_text())
    next(r for r in p['resolved'] if r['function']=='FUN_00755a60')['domain']='unknown'
    f=tmp_path/'bad.json'; f.write_text(json.dumps(p))
    with pytest.raises(ValueError): m.load_upstream(f)

def test_machine_plan_has_no_selected_local_write():
    m=load_module()
    assert set(m.WRITE_SITES['FUN_00755a60'].values())=={0x7b0,0x7b8,0x7c0,0x7c8,0x7f8,0x800,0x850}
    assert set(m.WRITE_SITES['FUN_00760b50'].values())=={0x368,0x868,0x888,0x8b0}
    assert set(m.WRITE_SITES['FUN_00752fc0'].values())=={0x5b8,0x7d8}
    assert all(0x538 not in set(v.values()) for v in m.WRITE_SITES.values())
    assert m.ANCHORS[0x00771177]=='lea ecx,[esi+0x2380]'
    assert m.ANCHORS[0x00755DB5]=='call 0x752fc0'

def test_pinned_retail_closure_stays_fail_closed():
    d=json.loads(EVIDENCE.read_text())
    assert d['format']=='SHIFT.P1D.Slot3ExactWheelDirectCarrierClosure/1'
    assert d['authority']['retail_executable_sha256']=='eca479aa2d8dbb88bc55709d91ae5c7159ae1b00fc9555d6701000c26de8aee1'
    assert d['selected_slot3']=={'hdvehicle_offset':'0x2380','local_target':'+0x538','absolute_target':'HDVehicle+0x28b8','width':'f64/qword'}
    assert d['paths']['fun00755a60']['target_overlap'] is False
    assert d['paths']['fun00755a60']['leaf_has_direct_calls'] is False
    assert d['paths']['fun00760b50']['target_overlap'] is False
    a=d['adjudication']
    assert a['slot3_fun00770e80_exact_wheel_direct_carrier_subset_complete'] is True
    assert a['deeper_direct_aliases_ruled_out'] is False
    assert a['indirect_callback_aliases_ruled_out'] is False
    assert a['slot3_writer_provenance_proven'] is False
    assert a['p1_3d_complete'] is False
    assert a['external_provider_count']==7
