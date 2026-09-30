import json
from pathlib import Path


def test_silverstone_runtime_shader_target_evidence_is_capture_ready():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence"
        / "silverstone_era3_runtime_shader_targets.json"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    result = report["result"]

    assert report["format"] == "SHIFT.IMBRuntimeShaderTargetSetEvidence/1"
    assert report["verification_scope"] == (
        "phase-568-silverstone-era3-runtime-shader-targets"
    )
    assert report["source_ranking"]["primitive_binding_count"] == 428
    assert report["source_ranking"]["unique_rank_context_count"] == 239
    assert report["source_ranking"]["selection_status_counts"] == {
        "ambiguous": 428
    }

    assert result["binding_target_count"] == 428
    assert result["capture_ready_binding_count"] == 428
    assert result["attribution_ready_binding_count"] == 0
    assert result["unique_hash_target_count"] == 51
    assert result["strong_hash_target_count"] == 0
    assert result["prefilter_only_target_count"] == 51
    assert result["target_kind_counts"] == {"pixel": 51}
    assert result["binding_hash_target_count_distribution"] == {
        "5": 175,
        "6": 156,
        "10": 73,
        "15": 24,
    }

    families = {
        row["family"]: row
        for row in report["families"]
    }
    assert {
        family: row["pixel_target_count"]
        for family, row in families.items()
    } == {
        "basicinstanced": 11,
        "crowdgeninstanced": 20,
        "crowdgeninstancedbillboard": 10,
        "foliageinstanced": 5,
        "skintestinstanced": 5,
    }

    all_hashes = []
    for row in families.values():
        assert row["pixel_target_count"] == len(
            row["pixel_shader_sha256"]
        )
        assert all(
            len(value) == 64
            and all(char in "0123456789abcdef" for char in value)
            for value in row["pixel_shader_sha256"]
        )
        all_hashes.extend(row["pixel_shader_sha256"])

    assert len(all_hashes) == 51
    assert len(set(all_hashes)) == 51

    assert report["boundary"]["all_bindings_capture_ready"] is True
    assert (
        report["boundary"]["all_bindings_exact_pair_attribution_ready"]
        is False
    )
    assert report["boundary"]["selects_permutation"] is False
