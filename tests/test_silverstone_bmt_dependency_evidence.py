import json
from pathlib import Path


def test_silverstone_bmt_dependency_evidence_has_only_global_shader_blockers():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence"
        / "silverstone_era3_bmt_dependencies.json"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    result = report["result"]

    assert report["format"] == "SHIFT.IMBMaterialDependencyEvidence/1"
    assert result["logical_bmt_reference_count"] == 84
    assert result["archive_bmt_occurrence_count"] == 239
    assert result["material_parse_count"] == 239
    assert result["material_parse_error_count"] == 0
    assert result["local_ready_count"] == 239
    assert result["texture_reference_count"] == 563
    assert result["same_archive_texture_resolved_count"] == 563
    assert result["same_archive_texture_missing_count"] == 0
    assert result["unique_shader_reference_count"] == 5
    assert result["fully_source_ready_count"] == 239
    assert result["shader_source_matches_in_render_count"] == 239
    assert len(report["shader_sources"]) == 5
    assert report["boundary"][
        "all_texture_references_resolve_in_same_silverstone_bff"
    ] is True
    assert report["boundary"][
        "all_five_shader_sources_resolve_exactly_once_in_render_bff"
    ] is True
