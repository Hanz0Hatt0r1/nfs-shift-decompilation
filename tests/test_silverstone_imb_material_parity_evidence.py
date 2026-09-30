import json
from pathlib import Path


def test_silverstone_imb_material_parity_evidence_is_closed():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence"
        / "silverstone_era3_imb_material_parity.json"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    result = report["result"]

    assert report["format"] == "SHIFT.IMBMaterialReferenceParityEvidence/1"
    assert result["imb_resource_count"] == 427
    assert result["primitive_reference_count"] == 428
    assert result["matched_primitive_reference_count"] == 428
    assert result["blocked_primitive_reference_count"] == 0
    assert result["unique_bmt_reference_count"] == 84
    assert result["missing_same_archive_count"] == 0
    assert result["ambiguous_same_archive_count"] == 0
    assert report["boundary"][
        "all_primitive_references_have_exactly_one_same_archive_bmt"
    ] is True
    assert report["boundary"]["all_matched_bmt_entries_use_bff_type2"] is True
