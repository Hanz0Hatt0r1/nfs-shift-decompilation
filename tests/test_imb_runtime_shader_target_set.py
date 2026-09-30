from imb_runtime_shader_target_set import (
    FORMAT,
    build_imb_runtime_shader_target_set,
)


def _sha(char):
    return char * 64


def _candidate(
    identity,
    *,
    pair="b",
    vertex="c",
    pixel="d",
    pair_status="unique",
    exact=True,
):
    return {
        "file": "render_shaders_basic_instanced_deadbeef.fxo",
        "program_offset": 128,
        "permutation_identity_sha256": _sha(identity),
        "pair_sha256": _sha(pair),
        "vertex_sha256": _sha(vertex),
        "pixel_sha256": _sha(pixel),
        "vertex_pair_selection_status": pair_status,
        "exact": exact,
    }


def _row(index, candidates, *, declared=None):
    return {
        "archive": "Silverstone_Era3_GrandPrix.bff",
        "imb_path": f"tracks/silverstone/object_{index}.imb",
        "imb_entry_index": 100 + index,
        "imb_sha256": _sha("a"),
        "primitive_index": 0,
        "draw_range": {
            "first_index": 30 + index * 3,
            "index_count": 6,
            "primitive_count": 2,
            "primitive_type": 4,
        },
        "property_descriptors": [
            {"id": "200", "words": [2, 0, 0]},
            {"id": "460", "words": [4, 6, 0]},
        ],
        "material_reference": "materials/test.mtx",
        "bmt": "materials/test.bmt",
        "bmt_sha256": _sha("e"),
        "shader": "render/shaders/basic_instanced.fx",
        "shader_family": "basicinstanced",
        "vertex_properties": ["200", "460", "220", "130"],
        "selection_status": "ambiguous",
        "top_rank_candidate_count": (
            len(candidates) if declared is None else declared
        ),
        "top_rank_candidates": candidates,
    }


def _ranking(*rows):
    return {
        "format": "SHIFT.IMBMaterialShaderRanking/1",
        "primitive_binding_count": len(rows),
        "runtime_target_count": len(rows),
        "unique_rank_context_count": len(rows),
        "rows": list(rows),
    }


def test_target_set_preserves_all_top_rank_identities_without_selecting_one():
    first = _candidate("1", pair="2", vertex="3", pixel="4")
    second = _candidate("5", pair="6", vertex="7", pixel="8")
    report = build_imb_runtime_shader_target_set(
        _ranking(
            _row(0, [first, second]),
            _row(1, [first]),
        )
    )

    assert report["format"] == FORMAT
    assert report["capture_ready"] is True
    assert report["attribution_ready"] is True
    assert report["binding_target_count"] == 2
    assert report["unique_hash_target_count"] == 2
    assert report["strong_hash_target_count"] == 2
    assert report["prefilter_only_target_count"] == 0
    assert report["boundary"]["selects_permutation"] is False

    row = report["binding_targets"][0]
    assert row["top_rank_candidate_count"] == 2
    assert row["hash_target_count"] == 2
    assert {target["identity_value"] for target in row["targets"]} == {
        _sha("1"),
        _sha("5"),
    }

    aggregate = {
        target["identity_value"]: target
        for target in report["unique_targets"]
    }
    assert aggregate[_sha("1")]["binding_indices"] == [0, 1]
    assert aggregate[_sha("5")]["binding_indices"] == [0]


def test_pair_ambiguous_candidate_falls_back_to_pixel_prefilter_target():
    report = build_imb_runtime_shader_target_set(
        _ranking(
            _row(
                0,
                [
                    _candidate(
                        "1",
                        pair_status="ambiguous",
                        pixel="9",
                    )
                ],
            )
        )
    )

    assert report["capture_ready"] is True
    assert report["attribution_ready"] is False
    assert report["strong_hash_target_count"] == 0
    assert report["prefilter_only_target_count"] == 1
    target = report["unique_targets"][0]
    assert target["identity_kind"] == "pixel"
    assert target["identity_value"] == _sha("9")
    assert target["strength"] == "prefilter-only"



def test_pixel_dedup_preserves_all_static_pair_variants():
    first = _candidate(
        "1",
        pair="2",
        vertex="3",
        pixel="9",
        pair_status="ambiguous",
    )
    second = _candidate(
        "4",
        pair="5",
        vertex="6",
        pixel="9",
        pair_status="ambiguous",
    )
    report = build_imb_runtime_shader_target_set(
        _ranking(_row(0, [first, second]))
    )

    assert report["capture_ready"] is True
    assert report["attribution_ready"] is False
    row = report["binding_targets"][0]
    assert row["imb_sha256"] == _sha("a")
    assert row["draw_range"] == {
        "first_index": 30,
        "index_count": 6,
        "primitive_count": 2,
        "primitive_type": 4,
    }
    assert row["property_descriptors"] == [
        {"id": "200", "words": [2, 0, 0]},
        {"id": "460", "words": [4, 6, 0]},
    ]

    assert row["hash_target_count"] == 1
    target = row["targets"][0]
    assert target["identity_kind"] == "pixel"
    assert target["identity_value"] == _sha("9")
    assert target["candidate_variant_count"] == 2
    assert target["vertex_byte_sha256"] is None
    assert target["pair_byte_sha256"] is None
    assert {
        variant["vertex_byte_sha256"]
        for variant in target["candidate_variants"]
    } == {_sha("3"), _sha("6")}
    assert {
        variant["pair_byte_sha256"]
        for variant in target["candidate_variants"]
    } == {_sha("2"), _sha("5")}
    assert report["boundary"]["preserves_candidate_variants"] is True

def test_incomplete_top_rank_list_fails_closed():
    report = build_imb_runtime_shader_target_set(
        _ranking(
            _row(
                0,
                [_candidate("1")],
                declared=2,
            )
        )
    )

    assert report["capture_ready"] is False
    assert report["status"] == "blocked"
    assert (
        "binding-0:top-rank-candidate-list-incomplete"
        in report["blocking_reasons"]
    )
    assert report["binding_targets"][0]["capture_ready"] is False


def test_unhashed_top_rank_candidate_is_explicit_blocker():
    candidate = {
        "file": "broken.fxo",
        "program_offset": 10,
        "vertex_pair_selection_status": "none",
        "exact": True,
    }
    report = build_imb_runtime_shader_target_set(
        _ranking(_row(0, [candidate]))
    )

    assert report["capture_ready"] is False
    assert "binding-0:no-hash-targets" in report["blocking_reasons"]
    assert (
        "binding-0:unhashed-top-candidates:1"
        in report["blocking_reasons"]
    )


def test_wrong_ranking_format_is_rejected():
    try:
        build_imb_runtime_shader_target_set(
            {"format": "SHIFT.Other/1"}
        )
    except ValueError as error:
        assert "SHIFT.IMBMaterialShaderRanking/1" in str(error)
    else:
        raise AssertionError("invalid ranking format was accepted")
