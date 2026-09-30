import json
from pathlib import Path


def test_silverstone_fxo_family_inventory_evidence_is_complete_and_ambiguous():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence"
        / "silverstone_era3_fxo_family_inventory.json"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    result = report["result"]

    assert report["format"] == "SHIFT.ShaderFamilyFXOInventoryEvidence/1"
    assert result["family_count"] == 5
    assert result["candidate_copy_count"] == 1280
    assert result["unique_decoded_payload_count"] == 368
    assert result["duplicate_copy_count"] == 912
    assert result["parse_failure_count"] == 0
    assert result["inventory_ready"] is True
    assert result["selection_ready"] is False

    families = {row["family"]: row for row in report["families"]}
    assert set(families) == {
        "basicinstanced",
        "crowdgeninstanced",
        "crowdgeninstancedbillboard",
        "foliageinstanced",
        "skintestinstanced",
    }

    assert (
        families["basicinstanced"]["candidate_copy_count"],
        families["basicinstanced"]["unique_payload_count"],
        families["basicinstanced"]["program_count_distribution"],
    ) == (192, 48, {"14": 192})
    assert (
        families["crowdgeninstanced"]["candidate_copy_count"],
        families["crowdgeninstanced"]["unique_payload_count"],
        families["crowdgeninstanced"]["program_count_distribution"],
    ) == (336, 96, {"14": 336})
    assert (
        families["crowdgeninstancedbillboard"]["candidate_copy_count"],
        families["crowdgeninstancedbillboard"]["unique_payload_count"],
        families["crowdgeninstancedbillboard"]["program_count_distribution"],
    ) == (320, 80, {"8": 320})
    assert (
        families["foliageinstanced"]["candidate_copy_count"],
        families["foliageinstanced"]["unique_payload_count"],
        families["foliageinstanced"]["program_count_distribution"],
    ) == (304, 112, {"10": 304})
    assert (
        families["skintestinstanced"]["candidate_copy_count"],
        families["skintestinstanced"]["unique_payload_count"],
        families["skintestinstanced"]["program_count_distribution"],
    ) == (128, 32, {"14": 128})

    assert report["boundary"]["all_target_families_present"] is True
    assert report["boundary"][
        "all_candidate_payloads_parse_as_d3d9_program_corpora"
    ] is True
    assert report["boundary"]["unique_static_permutation_selected"] is False
