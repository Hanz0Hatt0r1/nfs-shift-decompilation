import json
from pathlib import Path

from bmw_m3_meb_evidence_parity import validate_bmw_meb_evidence


ROOT=Path(__file__).resolve().parents[1]


def _load(name):
    return json.loads((ROOT/"evidence"/name).read_text(encoding="utf-8"))


def test_committed_bmw_meb_snapshot_matches_golden_manifest():
    evidence=_load("bmw_m3_e36_kit00_body_loda.meb.json")
    golden=_load("bmw_m3_e36_kit00_body_loda.golden.json")
    report=validate_bmw_meb_evidence(evidence,golden)
    assert report["ready"] is True
    assert report["blocking_reasons"] == []
    assert len(report["property_descriptors"]) == 8
    assert len(report["property_layouts"]) == 8
    assert len(report["primitives"]) == 6


def test_bmw_meb_snapshot_detects_primitive_drift():
    evidence=_load("bmw_m3_e36_kit00_body_loda.meb.json")
    golden=_load("bmw_m3_e36_kit00_body_loda.golden.json")
    evidence["mesh"]["primitives"][1]["index_count"] += 3
    report=validate_bmw_meb_evidence(evidence,golden)
    assert report["ready"] is False
    assert "meb:primitive-definition-mismatch" in report["blocking_reasons"]


def test_bmw_meb_snapshot_detects_property_layout_drift():
    evidence=_load("bmw_m3_e36_kit00_body_loda.meb.json")
    golden=_load("bmw_m3_e36_kit00_body_loda.golden.json")
    evidence["mesh"]["property_layouts"][0]["stride"] = 16
    report=validate_bmw_meb_evidence(evidence,golden)
    assert report["ready"] is False
    assert "meb:property-layout-mismatch" in report["blocking_reasons"]
