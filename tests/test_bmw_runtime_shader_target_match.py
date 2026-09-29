from bmw_runtime_shader_target_match import (
    FORMAT,
    match_bmw_runtime_shader_targets,
)


def _target_set(*, shared_identity=False, pixel_only=False):
    def target(value):
        if pixel_only:
            return {
                "identity_kind": "pixel",
                "identity_value": value,
                "strength": "prefilter-only",
                "permutation_identity_sha256": None,
                "pair_byte_sha256": None,
                "vertex_byte_sha256": None,
                "pixel_byte_sha256": value,
            }
        return {
            "identity_kind": "permutation",
            "identity_value": value,
            "strength": "exact-pair",
            "permutation_identity_sha256": value,
            "pair_byte_sha256": "b" * 64,
            "vertex_byte_sha256": "c" * 64,
            "pixel_byte_sha256": "d" * 64,
        }

    second = "a" * 64 if shared_identity else "e" * 64
    return {
        "format": "SHIFT.BMWRuntimeShaderTargetSet/1",
        "capture_ready": True,
        "target_resource": {
            "path": "vehicles/bmw/body.meb",
            "sha256": "f" * 64,
        },
        "primitive_targets": [
            {
                "primitive_index": 1,
                "material_ref": "vehicles/bmw/paint.mtx",
                "draw_range": {
                    "first_index": 150,
                    "index_count": 300,
                    "primitive_count": 100,
                },
                "targets": [target("a" * 64)],
            },
            {
                "primitive_index": 2,
                "material_ref": "vehicles/bmw/paint.mtx",
                "draw_range": {
                    "first_index": 450,
                    "index_count": 600,
                    "primitive_count": 200,
                },
                "targets": [target(second)],
            },
        ],
    }


def _identity(value, *, pixel="d" * 64):
    return {
        "format": "SHIFT.ShaderPermutationIdentity/1",
        "identity_sha256": value,
        "pair_byte_sha256": "b" * 64,
        "payload": {
            "vertex": {"byte_sha256": "c" * 64},
            "pixel": {"byte_sha256": pixel},
        },
    }


def _runtime(draws, identities, *, proven=True, resource="f" * 64):
    frames = []
    candidates = []
    for frame_index, (draw, identity) in enumerate(zip(draws, identities), 1):
        frames.append({
            "frame": frame_index,
            "vertex_declaration": {
                "resource_sha256": resource,
                "resource_path": "vehicles/bmw/body.meb",
            },
            "shader_permutation_identity": identity,
            "draws": [draw],
        })
        if proven:
            candidates.append({
                "frame": frame_index,
                "draw_index": 0,
            })
    return {
        "format": "SHIFT.D3D9RuntimeBindingEvidence/1",
        "frames": frames,
        "same_instance_gate": {
            "ready": proven,
            "candidate_frames": candidates,
        },
    }


def test_target_match_attributes_each_exact_draw_range_and_identity():
    report = match_bmw_runtime_shader_targets(
        _target_set(),
        _runtime(
            [
                {"start_index": 150, "primitive_count": 100},
                {"start_index": 450, "primitive_count": 200},
            ],
            [_identity("a" * 64), _identity("e" * 64)],
        ),
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["summary"]["attributed_primitive_count"] == 2
    assert [
        row["selected_identity"]["value"]
        for row in report["primitive_results"]
    ] == ["a" * 64, "e" * 64]


def test_target_match_uses_draw_range_to_separate_shared_shader_identity():
    report = match_bmw_runtime_shader_targets(
        _target_set(shared_identity=True),
        _runtime(
            [
                {"start_index": 150, "primitive_count": 100},
                {"start_index": 450, "primitive_count": 200},
            ],
            [_identity("a" * 64), _identity("a" * 64)],
        ),
    )

    assert report["ready"] is True
    assert [row["primitive_index"] for row in report["primitive_results"]] == [1, 2]
    assert all(row["attributed"] for row in report["primitive_results"])


def test_target_match_does_not_attribute_prefilter_only_pixel_hash():
    target_set = _target_set(pixel_only=True)
    report = match_bmw_runtime_shader_targets(
        target_set,
        _runtime(
            [
                {"start_index": 150, "primitive_count": 100},
                {"start_index": 450, "primitive_count": 200},
            ],
            [
                _identity("x" * 64, pixel="a" * 64),
                _identity("y" * 64, pixel="e" * 64),
            ],
        ),
    )

    assert report["ready"] is False
    assert report["status"] == "partial"
    assert report["summary"]["observed_primitive_count"] == 2
    assert report["summary"]["attributed_primitive_count"] == 0
    assert all(
        "only-prefilter-hash-matched" in row["blocking_reasons"][0]
        for row in report["primitive_results"]
    )


def test_target_match_requires_same_instance_gate():
    report = match_bmw_runtime_shader_targets(
        _target_set(),
        _runtime(
            [
                {"start_index": 150, "primitive_count": 100},
                {"start_index": 450, "primitive_count": 200},
            ],
            [_identity("a" * 64), _identity("e" * 64)],
            proven=False,
        ),
    )

    assert report["ready"] is False
    assert report["summary"]["attributed_primitive_count"] == 0
    assert "runtime-target:same-instance-gate-not-ready" in report["blocking_reasons"]


def test_target_match_rejects_wrong_resource_even_with_matching_shader():
    report = match_bmw_runtime_shader_targets(
        _target_set(),
        _runtime(
            [{"start_index": 150, "primitive_count": 100}],
            [_identity("a" * 64)],
            resource="0" * 64,
        ),
    )

    assert report["status"] == "not-found"
    assert report["summary"]["observed_primitive_count"] == 0


def test_target_match_rejects_wrong_draw_range():
    report = match_bmw_runtime_shader_targets(
        _target_set(),
        _runtime(
            [{"start_index": 151, "primitive_count": 100}],
            [_identity("a" * 64)],
        ),
    )

    assert report["status"] == "not-found"
    assert report["summary"]["observed_primitive_count"] == 0


def test_target_match_rejects_wrong_formats():
    try:
        match_bmw_runtime_shader_targets(
            {"format": "wrong"},
            {"format": "SHIFT.D3D9RuntimeBindingEvidence/1"},
        )
    except ValueError as error:
        assert "BMWRuntimeShaderTargetSet" in str(error)
    else:
        raise AssertionError("wrong target format must be rejected")



def test_prefilter_only_target_cannot_upgrade_via_representative_pair_hash():
    target_set = _target_set(pixel_only=True)
    # A real ambiguous static row may still carry a representative pair hash.
    for primitive in target_set["primitive_targets"]:
        primitive["targets"][0]["pair_byte_sha256"] = "b" * 64
    report = match_bmw_runtime_shader_targets(
        target_set,
        _runtime(
            [
                {"start_index": 150, "primitive_count": 100},
                {"start_index": 450, "primitive_count": 200},
            ],
            [
                _identity("x" * 64, pixel="a" * 64),
                _identity("y" * 64, pixel="e" * 64),
            ],
        ),
    )

    assert report["ready"] is False
    assert report["summary"]["attributed_primitive_count"] == 0
    assert all(
        row["best_score"] is None
        for row in report["primitive_results"]
    )
