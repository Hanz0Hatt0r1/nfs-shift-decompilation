from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "build_bmw_vehicle_render_model_resource_join.py"
SPEC = importlib.util.spec_from_file_location("build_bmw_vehicle_render_model_resource_join", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


@dataclass
class FakeEntry:
    index: int
    path: str
    type: int = 2
    compressed_size: int = 10
    uncompressed_size: int = 20


CRD = b'''<?xml version="1.0" ?>
<Reflection>
  <data class="VehicleDetails" id="0x2A6C460">
    <prop name="Name" data="BMW_M3_E36" />
    <prop name="Vehicle Render Model" data="BMW_M3_E36.vhf" />
  </data>
</Reflection>
'''

VHF = b'''<?xml version="1.0" encoding="utf-8" ?>
<CAR Name="BMW_M3_E36">
  <NODE type="HIERARCHY" Name="Root" MatrixNumber="0">
    <MATRIX id="0" Offset="0 0 0" Orientation="0 0 0 1" />
  </NODE>
</CAR>
'''


class FakeBFF:
    archives: dict[str, tuple[list[FakeEntry], dict[str, bytes]]] = {}

    def __init__(self, path):
        self.path = Path(path)
        entries, payloads = self.archives[self.path.name]
        self.entries = entries
        self.payloads = payloads

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def extract_entry(self, entry):
        return self.payloads[entry.path]


def _owner(path: Path, *, field: str = "+0x54", ready: bool = True) -> Path:
    path.write_text(
        json.dumps(
            {
                "format": m.OWNER_FORMAT,
                "ready": True,
                "vehicle_descriptor": {
                    "render_model_property_name": m.PROPERTY_NAME,
                    "render_model_field": field,
                },
                "handoff": {"vehicle_render_hierarchy_owner_ready": ready},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _file(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(name.encode("ascii"))
    return path


def _install_positive_archives(monkeypatch) -> None:
    descriptor_entry = FakeEntry(32, m.DESCRIPTOR_PATH)
    vhf_path = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
    FakeBFF.archives = {
        "VehiclesGlobal.bff": ([descriptor_entry], {m.DESCRIPTOR_PATH: CRD}),
        "VehiclesPersistent.bff": ([FakeEntry(27, m.DESCRIPTOR_PATH)], {m.DESCRIPTOR_PATH: CRD}),
        "BMW_M3_E36.bff": ([FakeEntry(1083, vhf_path, uncompressed_size=len(VHF))], {vhf_path: VHF}),
    }
    monkeypatch.setattr(m, "BFF", FakeBFF)


def test_proves_exact_bmw_descriptor_to_vhf_resource_join(tmp_path, monkeypatch):
    _install_positive_archives(monkeypatch)
    report = m.analyze(
        _owner(tmp_path / "owner.json"),
        _file(tmp_path, "BMW_M3_E36.bff"),
        [_file(tmp_path, "VehiclesGlobal.bff"), _file(tmp_path, "VehiclesPersistent.bff")],
    )

    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    descriptor = report["selected_vehicle_descriptor"]
    assert descriptor["property_value"] == "BMW_M3_E36.vhf"
    assert descriptor["selected_BMW_vehicle_render_model_value_ready"] is True
    resource = report["canonical_bmw_vhf_resource"]
    assert resource["resolved_path"] == "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
    assert resource["root_name"] == "BMW_M3_E36"
    assert resource["root_node_type"] == "HIERARCHY"
    assert resource["canonical_BMW_VHF_resource_join_ready"] is True
    assert report["handoff"]["outer_vehicle_root_to_VHF_vehicle_root_ready"] is False
    assert report["handoff"]["BODY0_bind_frame_proof_ready"] is False


def test_rejects_owner_property_offset_drift(tmp_path, monkeypatch):
    _install_positive_archives(monkeypatch)
    with pytest.raises(ValueError, match=r"\+0x54 proof drift"):
        m.analyze(
            _owner(tmp_path / "owner.json", field="+0x58"),
            _file(tmp_path, "BMW_M3_E36.bff"),
            [_file(tmp_path, "VehiclesGlobal.bff")],
        )


def test_rejects_descriptor_value_disagreement(tmp_path, monkeypatch):
    _install_positive_archives(monkeypatch)
    changed = CRD.replace(b"BMW_M3_E36.vhf", b"BMW_M3_E36_ALT.vhf")
    FakeBFF.archives["VehiclesPersistent.bff"] = (
        [FakeEntry(27, m.DESCRIPTOR_PATH)],
        {m.DESCRIPTOR_PATH: changed},
    )
    with pytest.raises(ValueError, match="descriptor copies disagree"):
        m.analyze(
            _owner(tmp_path / "owner.json"),
            _file(tmp_path, "BMW_M3_E36.bff"),
            [_file(tmp_path, "VehiclesGlobal.bff"), _file(tmp_path, "VehiclesPersistent.bff")],
        )


def test_rejects_ambiguous_vhf_logical_path(tmp_path, monkeypatch):
    _install_positive_archives(monkeypatch)
    path = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
    FakeBFF.archives["BMW_M3_E36.bff"] = (
        [FakeEntry(1083, path), FakeEntry(1084, path)],
        {path: VHF},
    )
    with pytest.raises(ValueError, match="matched 2 entries"):
        m.analyze(
            _owner(tmp_path / "owner.json"),
            _file(tmp_path, "BMW_M3_E36.bff"),
            [_file(tmp_path, "VehiclesGlobal.bff")],
        )


def test_rejects_vhf_vehicle_identity_drift(tmp_path, monkeypatch):
    _install_positive_archives(monkeypatch)
    path = "vehicles/bmw_m3_e36/bmw_m3_e36.vhf"
    wrong = VHF.replace(b'Name="BMW_M3_E36"', b'Name="BMW_M3_E46"')
    FakeBFF.archives["BMW_M3_E36.bff"] = (
        [FakeEntry(1083, path)],
        {path: wrong},
    )
    with pytest.raises(ValueError, match="root identity"):
        m.analyze(
            _owner(tmp_path / "owner.json"),
            _file(tmp_path, "BMW_M3_E36.bff"),
            [_file(tmp_path, "VehiclesGlobal.bff")],
        )
