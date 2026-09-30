import json
from pathlib import Path


def test_silverstone_runtime_resource_draw_identity_is_complete():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence"
        / "silverstone_era3_runtime_resource_draw_identity.json"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    result = report["result"]

    assert report["format"] == (
        "SHIFT.IMBRuntimeResourceDrawIdentityEvidence/1"
    )
    assert report["verification_scope"] == (
        "phase-570-silverstone-era3-runtime-resource-draw-identity"
    )
    assert report["source_archive"]["sha256"] == (
        "5423f5a0356e664a504f90c812e32bbbd4e2a0abe83c546fdc658305661a1e2f"
    )

    assert result["primitive_binding_count"] == 428
    assert result["resource_occurrence_count"] == 427
    assert result["unique_decoded_imb_sha256_count"] == 181
    assert result["logical_resource_path_count"] == 181
    assert result["logical_paths_with_multiple_decoded_hashes"] == 0
    assert result["resource_identity_ready_count"] == 428
    assert result["draw_range_ready_count"] == 428
    assert result["same_instance_target_ready_count"] == 428
    assert result["resource_primitive_count_distribution"] == {
        "1": 426,
        "2": 1,
    }
    assert result["index_count_min"] == 6
    assert result["index_count_max"] == 3072

    multi = report["multi_primitive_resources"]
    assert len(multi) == 1
    assert multi[0]["path"] == (
        "tracks/_data/instances/gen_tent18_loda.imb"
    )
    assert [
        (row["primitive_index"], row["first_index"], row["index_count"])
        for row in multi[0]["primitives"]
    ] == [
        (0, 0, 96),
        (1, 96, 24),
    ]
    assert len({
        row["imb_sha256"]
        for row in multi[0]["primitives"]
    }) == 1

    boundary = report["boundary"]
    assert boundary[
        "all_primitive_bindings_resource_identity_ready"
    ] is True
    assert boundary["all_primitive_bindings_draw_range_ready"] is True
    assert boundary["same_instance_runtime_observation"] == "not evaluated"
