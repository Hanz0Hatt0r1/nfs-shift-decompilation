from bmw_runtime_shader_target_set import (
    FORMAT,
    build_bmw_runtime_shader_target_set,
)


def _candidate(
    identity,
    *,
    pair="2" * 64,
    vertex="3" * 64,
    pixel="4" * 64,
    file="a.fxo",
    offset=100,
    pair_status="unique",
    score=4,
):
    return {
        "file": file,
        "program_offset": offset,
        "exact": True,
        "score": score,
        "vertex_pair_valid": True,
        "vertex_pair_score": 1.0,
        "uniform_coverage": 1.0,
        "specialization_score": 1.0,
        "specialization_contradicted": [],
        "specialization_unexpected": [],
        "uniform_matches": ["u"],
        "vertex_pair_selection_status": pair_status,
        "pair_sha256": pair,
        "vertex_sha256": vertex,
        "pixel_sha256": pixel,
        "permutation_identity": (
            {
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": identity,
            }
            if identity is not None else None
        ),
    }


def _slice(index, candidates, *, material="paint"):
    return {
        "format": "SHIFT.BMWMaterialSlice/1",
        "status": "blocked",
        "ready": False,
        "blocking_reasons": [
            "generic-material:shader-selection-not-unique"
        ],
        "primitive_index": index,
        "material_ref": f"vehicles/bmw/{material}.mtx",
        "material_bmt": f"vehicles/bmw/{material}.bmt",
        "golden_identity": {
            "resource": "vehicles/bmw/body.meb",
            "resource_sha256": "a" * 64,
        },
        "provenance": {
            "mesh_entry": {
                "path": "vehicles/bmw/body.meb",
                "sha256": "a" * 64,
            }
        },
        "material_binding": {
            "selection_status": "ambiguous",
            "fxo_candidates": candidates,
        },
    }


def _admission(rows):
    indices = [row["primitive_index"] for row in rows]
    return {
        "format": "SHIFT.BMWBodyMaterialAdmission/1",
        "status": "blocked",
        "ready": False,
        "selection": {
            "primitive_indices": indices,
            "canonical_primitives": [
                {
                    "primitive_index": index,
                    "first_index": index * 300,
                    "index_count": 300,
                    "material": f"vehicles/bmw/material_{index}.mtx",
                }
                for index in indices
            ],
        },
        "primitive_results": [
            {
                "primitive_index": row["primitive_index"],
                "ready": False,
                "slice": row,
            }
            for row in rows
        ],
    }


def test_shader_target_set_preserves_all_top_rank_identities():
    first = _candidate("1" * 64, file="a.fxo", offset=100)
    second = _candidate("5" * 64, pair="6" * 64, file="b.fxo", offset=200)
    report = build_bmw_runtime_shader_target_set(
        _admission([_slice(0, [first, second])])
    )

    assert report["format"] == FORMAT
    assert report["capture_ready"] is True
    assert report["attribution_ready"] is True
    assert report["unique_hash_target_count"] == 2
    primitive = report["primitive_targets"][0]
    assert primitive["top_rank_candidate_count"] == 2
    assert primitive["hash_target_count"] == 2
    assert primitive["draw_range"] == {
        "first_index": 0,
        "index_count": 300,
        "primitive_count": 100,
    }
    assert {
        row["identity_value"] for row in primitive["targets"]
    } == {"1" * 64, "5" * 64}


def test_shader_target_set_excludes_statically_dominated_candidates():
    best = _candidate("1" * 64, score=5)
    worse = _candidate(
        "5" * 64,
        pair="6" * 64,
        file="worse.fxo",
        offset=200,
        score=4,
    )
    report = build_bmw_runtime_shader_target_set(
        _admission([_slice(0, [best, worse])])
    )

    primitive = report["primitive_targets"][0]
    assert primitive["top_rank_candidate_count"] == 1
    assert primitive["targets"][0]["identity_value"] == "1" * 64


def test_shader_target_set_collapses_same_identity_across_locations():
    first = _candidate("1" * 64, file="a.fxo", offset=100)
    second = _candidate("1" * 64, file="copy.fxo", offset=900)
    report = build_bmw_runtime_shader_target_set(
        _admission([_slice(0, [first, second])])
    )

    primitive = report["primitive_targets"][0]
    assert primitive["hash_target_count"] == 1
    locations = primitive["targets"][0]["candidate_locations"]
    assert locations == [
        {"file": "a.fxo", "program_offset": 100},
        {"file": "copy.fxo", "program_offset": 900},
    ]


def test_shader_target_set_uses_pixel_prefilter_for_ambiguous_vertex_pair():
    candidate = _candidate(
        None,
        pair=None,
        pair_status="ambiguous",
        pixel="4" * 64,
    )
    report = build_bmw_runtime_shader_target_set(
        _admission([_slice(1, [candidate])])
    )

    assert report["capture_ready"] is True
    assert report["attribution_ready"] is False
    assert report["prefilter_only_target_count"] == 1
    target = report["primitive_targets"][0]["targets"][0]
    assert target["identity_kind"] == "pixel"
    assert target["strength"] == "prefilter-only"


def test_shader_target_set_groups_shared_material_identity_across_primitives():
    candidate = _candidate("1" * 64)
    report = build_bmw_runtime_shader_target_set(
        _admission([
            _slice(1, [candidate], material="paint"),
            _slice(2, [candidate], material="paint"),
        ])
    )

    assert report["unique_hash_target_count"] == 1
    assert report["unique_targets"][0]["primitive_indices"] == [1, 2]


def test_shader_target_set_blocks_missing_slice():
    admission = {
        "format": "SHIFT.BMWBodyMaterialAdmission/1",
        "selection": {"primitive_indices": [0]},
        "primitive_results": [
            {"primitive_index": 0, "ready": False, "slice": None}
        ],
    }
    report = build_bmw_runtime_shader_target_set(admission)

    assert report["capture_ready"] is False
    assert (
        "shader-target:primitive-0:slice-missing"
        in report["blocking_reasons"]
    )


def test_shader_target_set_rejects_wrong_input_format():
    try:
        build_bmw_runtime_shader_target_set({"format": "wrong"})
    except ValueError as error:
        assert "BMWBodyMaterialAdmission" in str(error)
    else:
        raise AssertionError("wrong admission format must be rejected")
