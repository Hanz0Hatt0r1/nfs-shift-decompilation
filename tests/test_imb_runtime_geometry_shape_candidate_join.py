import hashlib
import json

from imb_runtime_geometry_shape_candidate_join import (
    CORPUS_FORMAT,
    FORMAT,
    PIPELINE_FORMAT,
    RUNTIME_FORMAT,
    build_runtime_geometry_shape_candidate_join,
)


def _sha(label):
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _canonical(value):
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


VS = _sha("vs")
PS = _sha("ps")
DECL = _sha("decl")


def _pipeline():
    return {
        "vertex_shader_sha256": VS,
        "pixel_shader_sha256": PS,
        "declaration_sha256": DECL,
        "stream_layout": [
            {"stream": 0, "stride": 80},
            {"stream": 1, "stride": 64},
        ],
        "index_format": 101,
    }


def _resource_shape(
    label,
    *,
    primitive_count,
    vertex_count,
    draw_count,
    texture_width,
):
    pipeline = _pipeline()
    signature = {
        **pipeline,
        "stream_resource_shapes": [
            {
                "stream": 0,
                "stride": 80,
                "length": vertex_count * 80,
                "usage": 0,
                "fvf": 0,
                "pool": 1,
            },
            {
                "stream": 1,
                "stride": 64,
                "length": 131072,
                "usage": 520,
                "fvf": 0,
                "pool": 0,
            },
        ],
        "index_resource_shape": {
            "length": primitive_count * 3 * 2,
            "format": 101,
            "usage": 0,
            "pool": 1,
        },
        "texture_stages": [{
            "stage": 1,
            "resource_type_name": "texture2d",
            "width": texture_width,
            "height": texture_width,
            "format": 827611204,
            "pool": 1,
            "level_count": 1,
            "usage": 0,
        }],
    }
    return {
        "signature_sha256": _sha(label),
        "signature": signature,
        "draw_count": draw_count,
        "primitive_count_sum": draw_count * primitive_count,
        "first_frame": 4287,
        "last_frame": 4308,
        "families": ["crowdgeninstanced"],
        "distinct_draw_range_count": 1,
        "observed_draw_ranges": [{
            "primitive_type": 4,
            "base_vertex_index": 0,
            "start_index": 0,
            "primitive_count": primitive_count,
            "draw_count": draw_count,
        }],
    }


def _content_group(label, *, primitive_count):
    return {
        "content_group_sha256": _sha(f"group-{label}"),
        "imb_sha256": _sha(f"imb-{label}"),
        "primitive_index": 0,
        "draw_range": {
            "first_index": 0,
            "index_count": primitive_count * 3,
            "primitive_count": primitive_count,
        },
        "bmt_sha256": _sha(f"bmt-{label}"),
        "shader_family": "crowdgeninstanced",
        "static_vertex_stride": 80,
        "matched_vertex_shader_sha256": None,
        "matched_pixel_shader_sha256": PS,
        "binding_indices": [1],
        "archives": ["Silverstone_Era3_Drift.bff"],
        "imb_paths": [f"characters/{label}.imb"],
        "static_binding_count": 1,
    }


def _pipeline_join(groups):
    pipeline_sha = _canonical(_pipeline())
    return {
        "format": PIPELINE_FORMAT,
        "pipeline_candidates": [{
            "runtime_signature_sha256": pipeline_sha,
            "candidate_content_status": "ambiguous-content-candidates",
            "candidate_content_groups": groups,
        }],
    }


def _corpus(rows):
    return {
        "format": CORPUS_FORMAT,
        "rows": rows,
    }


def _corpus_row(label, *, vertex_count, triangle_count):
    return {
        "ready": True,
        "decoded_sha256": _sha(f"imb-{label}"),
        "vertex_count": vertex_count,
        "primitive_count": 1,
        "triangle_count": triangle_count,
    }


def test_geometry_shape_join_splits_pipeline_by_geometry_and_collapses_textures():
    group24 = _content_group("lodc", primitive_count=24)
    group72 = _content_group("lodb", primitive_count=72)
    runtime = {
        "format": RUNTIME_FORMAT,
        "resource_shape_signatures": [
            _resource_shape(
                "24-a",
                primitive_count=24,
                vertex_count=28,
                draw_count=3,
                texture_width=128,
            ),
            _resource_shape(
                "24-b",
                primitive_count=24,
                vertex_count=28,
                draw_count=2,
                texture_width=256,
            ),
            _resource_shape(
                "72",
                primitive_count=72,
                vertex_count=60,
                draw_count=4,
                texture_width=512,
            ),
        ],
    }
    pipeline = _pipeline_join([group24, group72])
    corpus = _corpus([
        _corpus_row("lodc", vertex_count=28, triangle_count=24),
        _corpus_row("lodb", vertex_count=60, triangle_count=72),
    ])

    report = build_runtime_geometry_shape_candidate_join(
        runtime,
        pipeline,
        corpus,
    )

    assert report["format"] == FORMAT
    summary = report["summary"]
    assert summary["runtime_resource_shape_signature_count"] == 3
    assert summary["runtime_geometry_shape_count"] == 2
    assert summary["runtime_geometry_shape_draw_count"] == 9
    assert summary["pipeline_linked_geometry_shape_count"] == 2
    assert summary["descriptor_gate_applied_geometry_shape_count"] == 2
    assert summary["single_content_candidate_geometry_shape_count"] == 2
    assert summary["single_content_candidate_draw_count"] == 9

    by_index_count = {
        row["runtime_index_count"]: row
        for row in report["geometry_shapes"]
    }
    shape24 = by_index_count[72]
    assert shape24["resource_shape_count"] == 2
    assert shape24["draw_count"] == 5
    assert shape24["runtime_vertex_count"] == 28
    assert shape24["candidate_content_group_count"] == 1
    assert shape24["candidate_content_group_sha256s"] == [
        group24["content_group_sha256"]
    ]
    assert (
        shape24["candidate_content_groups"][0][
            "descriptor_geometry_match"
        ]
        is True
    )

    shape72 = by_index_count[216]
    assert shape72["resource_shape_count"] == 1
    assert shape72["runtime_vertex_count"] == 60
    assert shape72["candidate_content_group_sha256s"] == [
        group72["content_group_sha256"]
    ]


def test_geometry_shape_descriptor_mismatch_falls_back_without_rejection():
    group = _content_group("mesh", primitive_count=24)
    runtime_shape = _resource_shape(
        "mismatch",
        primitive_count=24,
        vertex_count=99,
        draw_count=2,
        texture_width=128,
    )
    runtime = {
        "format": RUNTIME_FORMAT,
        "resource_shape_signatures": [runtime_shape],
    }
    pipeline = _pipeline_join([group])
    corpus = _corpus([
        _corpus_row("mesh", vertex_count=28, triangle_count=24),
    ])

    report = build_runtime_geometry_shape_candidate_join(
        runtime,
        pipeline,
        corpus,
    )

    row = report["geometry_shapes"][0]
    assert row["descriptor_gate_status"] == "no-exact-match-fallback"
    assert row["candidate_content_group_count"] == 1
    assert row["candidate_content_group_sha256s"] == [
        group["content_group_sha256"]
    ]
    assert row["candidate_content_groups"][0][
        "descriptor_match_complete"
    ] is True
    assert row["candidate_content_groups"][0][
        "descriptor_geometry_match"
    ] is False
    assert (
        report["summary"][
            "descriptor_gate_fallback_geometry_shape_count"
        ]
        == 1
    )


def test_geometry_shape_join_rejects_wrong_contracts():
    runtime = {
        "format": RUNTIME_FORMAT,
        "resource_shape_signatures": [],
    }
    pipeline = {
        "format": PIPELINE_FORMAT,
        "pipeline_candidates": [],
    }
    corpus = {
        "format": CORPUS_FORMAT,
        "rows": [],
    }

    for values, expected in [
        (({"format": "wrong"}, pipeline, corpus), "runtime catalog"),
        ((runtime, {"format": "wrong"}, corpus), "pipeline join"),
        ((runtime, pipeline, {"format": "wrong"}), "corpus audit"),
    ]:
        try:
            build_runtime_geometry_shape_candidate_join(*values)
        except ValueError as error:
            assert expected in str(error)
        else:
            raise AssertionError("wrong contract must fail")
