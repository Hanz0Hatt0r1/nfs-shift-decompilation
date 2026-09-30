import json
from pathlib import Path


def test_silverstone_material_shader_ranking_evidence_is_complete():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence"
        / "silverstone_era3_material_shader_ranking.json"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    result = report["result"]

    assert report["format"] == "SHIFT.IMBMaterialShaderRankingEvidence/1"
    assert result["primitive_binding_count"] == 428
    assert result["unique_rank_context_count"] == 239
    assert result["selection_status_counts"] == {"ambiguous": 428}
    assert result["unique_selection_count"] == 0
    assert result["ambiguous_selection_count"] == 428
    assert result["heuristic_selection_count"] == 0
    assert result["no_selection_count"] == 0
    assert result["runtime_target_count"] == 428

    families = {row["family"]: row for row in report["families"]}
    assert {
        name: row["primitive_binding_count"]
        for name, row in families.items()
    } == {
        "basicinstanced": 238,
        "crowdgeninstanced": 84,
        "crowdgeninstancedbillboard": 61,
        "foliageinstanced": 37,
        "skintestinstanced": 8,
    }
    assert {
        name: row["unique_rank_context_count"]
        for name, row in families.items()
    } == {
        "basicinstanced": 114,
        "crowdgeninstanced": 40,
        "crowdgeninstancedbillboard": 44,
        "foliageinstanced": 37,
        "skintestinstanced": 4,
    }
    assert {
        name: row["distinct_tied_permutation_identity_count"]
        for name, row in families.items()
    } == {
        "basicinstanced": 11,
        "crowdgeninstanced": 20,
        "crowdgeninstancedbillboard": 10,
        "foliageinstanced": 5,
        "skintestinstanced": 5,
    }

    identities = {
        identity
        for row in families.values()
        for identity in row["tied_permutation_identity_sha256"]
    }
    assert len(identities) == 51
    assert report["boundary"]["production_contexts_complete"] is True
    assert report["boundary"]["heuristic_or_missing_selection"] is False
    assert report["boundary"]["static_unique_selection"] is False
    assert report["boundary"]["runtime_shader_attribution_required"] is True


def test_ambiguity_distribution_covers_every_primitive_binding():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence"
        / "silverstone_era3_material_shader_ranking.json"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    distribution = {
        int(count): rows
        for count, rows in report[
            "ambiguous_candidate_count_distribution"
        ].items()
    }
    assert distribution == {
        5: 37,
        6: 156,
        20: 118,
        30: 20,
        40: 25,
        60: 48,
        120: 24,
    }
    assert sum(distribution.values()) == 428
