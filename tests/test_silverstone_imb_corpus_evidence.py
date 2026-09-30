import json
from pathlib import Path


def test_silverstone_era3_imb_corpus_evidence_is_closed():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence"
        / "silverstone_era3_imb_corpus.json"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    result = report["result"]

    assert report["format"] == "SHIFT.IMBCorpusAuditEvidence/1"
    assert result["resource_count"] == 427
    assert result["decoded_count"] == 427
    assert result["decode_error_count"] == 0
    assert result["version_counts"] == {"0.4.0.0": 427}
    assert result["total_vertex_count"] == 96872
    assert result["total_primitive_count"] == 428
    assert result["total_triangle_count"] == 105336
    assert result["bone_resource_count"] == 92
    assert result["trailing_byte_counts"] == {"0": 427}
    assert report["boundary"][
        "all_observed_property_ids_supported_by_phase560_adapter"
    ] is True

    visual = {
        row["name"]: row["imb_count"]
        for row in report["archives"]
        if not row["name"].endswith("_Physics.bff")
    }
    assert visual == {
        "Silverstone_Era3_Drift.bff": 117,
        "Silverstone_Era3_GrandPrix.bff": 103,
        "Silverstone_Era3_International.bff": 99,
        "Silverstone_Era3_National.bff": 108,
    }
