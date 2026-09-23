from skinned_draw import build_skinned_draw_contract


def _packet():
    return {
        "scene": {"archive": "CAR.bff", "path": "cars/body.vhf"},
        "node": {"name": "BODY", "type": "OBJECT", "matrix": "0"},
        "mesh": {
            "ref": "cars/body.meb",
            "resolved": {"path": "cars/body.meb"},
            "vertex_count": 1,
            "triangle_count": 0,
            "skinning": {
                "skinned": True,
                "valid": True,
                "bone_count": 2,
            },
        },
        "submeshes": [{"first_index": 0, "index_count": 0, "material": {}}],
    }


def _pose():
    return [
        {"matrix_3x4": [1,0,0,0, 0,1,0,0, 0,0,1,0]},
        {"matrix_3x4": [1,0,0,10, 0,1,0,0, 0,0,1,0]},
    ]


def test_skinned_draw_requires_pose():
    r = build_skinned_draw_contract(_packet())
    assert r["ready"] is False
    assert "pose:missing" in r["blocking_reasons"]


def test_skinned_draw_accepts_valid_pose_and_influences():
    r = build_skinned_draw_contract(
        _packet(),
        pose_bones=_pose(),
        bone_indices=[(0, 1, 0, 0)],
        bone_weights=[(0.5, 0.5, 0.0, 0.0)],
    )
    assert r["ready"] is True
    assert r["pose"]["bone_count"] == 2
    assert r["influence_validation"]["valid"] is True


def test_skinned_draw_rejects_pose_count_mismatch():
    r = build_skinned_draw_contract(_packet(), pose_bones=_pose()[:1])
    assert r["ready"] is False
    assert "pose:bone-count-mismatch" in r["blocking_reasons"]
