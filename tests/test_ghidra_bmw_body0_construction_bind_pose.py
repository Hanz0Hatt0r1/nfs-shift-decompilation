from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import dataclass
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "ghidra" / "build_bmw_body0_construction_bind_pose.py"
spec = importlib.util.spec_from_file_location("body0_construction_bind", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


SDF = b"""// synthetic canonical shape\n[BODY]\nname=body mass=(0.0) inertia=(0,0,0)\npos=(0,0,0) ori=(0,0,0)\n\n[BODY]\nname=fl_spindle pos=(1,0,-1) ori=(0,0,0)\n\n[BODY]\nname=fr_spindle pos=(-1,0,-1) ori=(0,0,0)\n\n[BODY]\nname=fl_wheel pos=(1,0,-1) ori=(0,0,0)\n\n[BODY]\nname=fr_wheel pos=(-1,0,-1) ori=(0,0,0)\n\n[BODY]\nname=rl_spindle pos=(1,0,1) ori=(0,0,0)\n\n[BODY]\nname=rr_spindle pos=(-1,0,1) ori=(0,0,0)\n\n[BODY]\nname=rl_wheel pos=(1,0,1) ori=(0,0,0)\n\n[BODY]\nname=rr_wheel pos=(-1,0,1) ori=(0,0,0)\n\n[BODY]\nname=fuel_tank pos=(0,0,0) ori=(0,0,0)\n\n[BODY]\nname=driver_head pos=(0,0,0) ori=(0,0,0)\n"""

VHF = b"""<?xml version='1.0'?>
<CAR Name='BMW_M3_E36'>
  <NODE type='HIERARCHY' Name='Root' MatrixNumber='0'>
    <MATRIX id='0' Offset='0 0 0' Orientation='0 0 0 1' />
    <MATRIX id='22' Offset='0 0 0' Orientation='0 0 0 1' parent='0' />
    <NODE type='OBJECT' Name='BMW_M3_E36_KIT00_BODY_LODA' MatrixNumber='22'>
      <RESOURCE Filename='vehicles\\BMW_M3_E36\\BMW_M3_E36_KIT00_BODY_LODA.meb' />
    </NODE>
  </NODE>
</CAR>
"""


@dataclass
class Entry:
    path: str


class FakeBFF:
    payloads: dict[str, bytes] = {}

    def __init__(self, path):
        self.path = path
        self.entries = [Entry(module.SDF_PATH), Entry(module.VHF_PATH)]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def extract_entry(self, entry):
        return self.payloads[entry.path]


def _run(monkeypatch, tmp_path: Path, *, sdf: bytes = SDF, vhf: bytes = VHF):
    archive = tmp_path / "BMW_M3_E36.bff"
    archive.write_bytes(b"synthetic-bff")
    FakeBFF.payloads = {module.SDF_PATH: sdf, module.VHF_PATH: vhf}
    monkeypatch.setattr(module, "BFF", FakeBFF)
    monkeypatch.setattr(module, "ARCHIVE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())
    monkeypatch.setattr(module, "SDF_SHA256", hashlib.sha256(sdf).hexdigest())
    monkeypatch.setattr(module, "VHF_SHA256", hashlib.sha256(vhf).hexdigest())
    return module.build_bmw_body0_construction_bind_pose(archive)


def test_body0_construction_pose_is_positive_but_root_join_stays_negative(monkeypatch, tmp_path):
    report = _run(monkeypatch, tmp_path)
    assert report["ready"] is True
    assert report["body0_resource_descriptor"]["body_index"] == 0
    assert report["body0_resource_descriptor"]["body_name"] == "body"
    assert report["construction_pose"]["row_matrix"] == module.IDENTITY_ROW
    assert report["construction_pose"]["BODY0_initial_pose_identity_proven"] is True
    assert report["machine_construction_chain"]["construction_path_uses_FUN_007b7840"] is False
    assert report["handoff"]["BODY0_construction_pose_ready"] is True
    assert report["handoff"]["physics_construction_root_equals_vhf_vehicle_root_proven"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False
    assert report["scope"]["matching_zero_offsets_used_as_root_frame_identity"] is False
    assert report["scope"]["BODY0_bind_matrix_proven"] is False


def test_nonzero_body0_position_fails_closed(monkeypatch, tmp_path):
    sdf = SDF.replace(b"pos=(0,0,0) ori=(0,0,0)", b"pos=(1,0,0) ori=(0,0,0)", 1)
    with pytest.raises(ValueError, match="BODY0 SDF position is not zero"):
        _run(monkeypatch, tmp_path, sdf=sdf)


def test_nonzero_body0_orientation_fails_closed(monkeypatch, tmp_path):
    sdf = SDF.replace(b"pos=(0,0,0) ori=(0,0,0)", b"pos=(0,0,0) ori=(0,1,0)", 1)
    with pytest.raises(ValueError, match="BODY0 SDF orientation is not zero"):
        _run(monkeypatch, tmp_path, sdf=sdf)


def test_nonidentity_vhf_body_matrix_fails_closed(monkeypatch, tmp_path):
    vhf = VHF.replace(b"id='22' Offset='0 0 0'", b"id='22' Offset='0 1 0'")
    with pytest.raises(ValueError, match="canonical VHF body Offset is not zero"):
        _run(monkeypatch, tmp_path, vhf=vhf)


def test_machine_chain_is_exact_and_count_increment_is_last():
    calls = module.DIRECT_CALLS
    assert [(row["caller"], row["callee"]) for row in calls] == [
        ("FUN_007b6900", "FUN_007b3670"),
        ("FUN_007b3670", "FUN_007bbb10"),
        ("FUN_007bbb10", "FUN_007b00a0"),
    ]
    assert calls[0]["callsite"] == 0x007B6E8F
    assert calls[1]["callsite"] == 0x007B37C8
    assert calls[2]["callsite"] == 0x007BBB3A
    origin = module.MACHINE_SIGNATURES["builder_origin_copy"]
    orientation = module.MACHINE_SIGNATURES["builder_orientation_forward"]
    increment = module.MACHINE_SIGNATURES["builder_count_increment"]
    assert origin["end"] <= orientation["start"] < increment["start"]
    assert module.MACHINE_SIGNATURES["x87_fsin"]["hex"] == "d9fe"
    assert module.MACHINE_SIGNATURES["x87_fcos"]["hex"] == "d9ff"


def test_retail_identity_constants_match_frozen_e36_corpus():
    assert module.ARCHIVE_SHA256 == "c31d34a0a7cab04bcff693fa0cbda3400f50d690a9c8bb2521b2882fc2a68d70"
    assert module.SDF_SHA256 == "fe0b18e95e81f87d67076b70890965a0a1384a925bfd836aaf5aa705fc4781ed"
    assert module.VHF_SHA256 == "e08887d17d9e34e703a385260f41017fc19acbebc3405614b375e81766b4bd51"
    assert module.BODY_OBJECT_NAME == "BMW_M3_E36_KIT00_BODY_LODA"
    assert module.BODY_MEB_PATH == "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
