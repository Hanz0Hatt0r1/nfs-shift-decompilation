from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "validate_bmw_offset33b_resource_inputs.py"
INPUTS = ROOT / "evidence" / "bmw_offset33b_resource_inputs.json"
MANIFEST = ROOT / "evidence" / "bmw_m3_vehicle_physics_manifest.json"
BODY0 = ROOT / "evidence" / "bmw_body0_bind_resource_materialization.json"


def _module():
    spec = importlib.util.spec_from_file_location("validate_offset33b_resources", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_bmw_offset33b_resource_inputs_validate() -> None:
    m = _module()
    report = m.validate(INPUTS, MANIFEST, BODY0)
    assert report["format"] == m.FORMAT
    assert report["ready"] is True
    assert report["cdf_direct_field_count"] == 4
    assert report["sdf_body_count"] == 11
    assert report["derived_load_data_frontier"] == ["+0x338"]
    handoff = report["handoff"]
    assert handoff["offset33b_resource_inputs_ready"] is True
    assert handoff["offset33b_memory_LOAD_semantic_join_ready"] is False
    assert handoff["BMW_numeric_offset33b_ready"] is False
    assert handoff["vehicle_world_transform_ready"] is False


def test_parser_to_load_data_offset_drift_fails_closed(tmp_path: Path) -> None:
    m = _module()
    value = json.loads(INPUTS.read_text(encoding="utf-8"))
    value["fun_0076b280_load_data_mapping"]["direct_fields"][0]["load_data_offsets"] = [0x25]
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="load-data offset drift"):
        m.validate(path, MANIFEST, BODY0)


def test_derived_0x338_cannot_be_silently_promoted(tmp_path: Path) -> None:
    m = _module()
    value = json.loads(INPUTS.read_text(encoding="utf-8"))
    value["fun_0076b280_load_data_mapping"]["derived_load_data_offsets_not_promoted_from_resource_name"] = []
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="derived load-data frontier"):
        m.validate(path, MANIFEST, BODY0)


def test_numeric_offset33b_preclaim_fails_closed(tmp_path: Path) -> None:
    m = _module()
    value = json.loads(INPUTS.read_text(encoding="utf-8"))
    value["handoff"]["BMW_numeric_offset33b_ready"] = True
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="fail-closed handoff drift"):
        m.validate(path, MANIFEST, BODY0)


def test_manifest_hash_drift_fails_closed(tmp_path: Path) -> None:
    m = _module()
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    value["archive_entry_points"][0]["sha256"] = "0" * 64
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest SHA drift"):
        m.validate(INPUTS, path, BODY0)
