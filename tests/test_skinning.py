from skinning import (
    build_skinning_contract,
    validate_influences,
    skin_points,
    skin_directions,
)


def _bones():
    return [
        {
            "index": 0,
            "matrix_3x4": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
        },
        {
            "index": 1,
            "matrix_3x4": [1, 0, 0, 10, 0, 1, 0, 0, 0, 0, 1, 0],
        },
    ]


def test_validate_influences_checks_bone_range_and_weight_shape():
    r = validate_influences(
        [(0, 1, 0, 0)],
        [(0.25, 0.75, 0.0, 0.0)],
        2,
    )
    assert r["valid"] is True
    bad = validate_influences([(0, 2, 0, 0)], [(1, 0, 0, 0)], 2)
    assert bad["valid"] is False
    assert any(x["kind"] == "bone-index-out-of-range" for x in bad["issues"])


def test_skin_points_translation_blends():
    out = skin_points(
        [(0, 0, 0)],
        [(0, 1, 0, 0)],
        [(0.5, 0.5, 0, 0)],
        _bones(),
    )
    assert out == [(5.0, 0.0, 0.0)]


def test_skin_points_can_normalize_source_weights():
    out = skin_points(
        [(0, 0, 0)],
        [(0, 1, 0, 0)],
        [(1.0, 1.0, 0, 0)],
        _bones(),
        normalize_weights=True,
    )
    assert out == [(5.0, 0.0, 0.0)]


def test_skin_directions_ignore_translation():
    out = skin_directions(
        [(1, 0, 0)],
        [(0, 1, 0, 0)],
        [(0.5, 0.5, 0, 0)],
        _bones(),
    )
    assert out == [(1.0, 0.0, 0.0)]


def test_unskinned_contract():
    r = build_skinning_contract(["200"], None)
    assert r["valid"] is True
    assert r["skinned"] is False


def test_mismatched_skin_attributes_are_invalid():
    r = build_skinning_contract(["200", "310"], None)
    assert r["valid"] is False
    assert r["error"] == "weights_without_indices"
