from native_scene_instance_transform_match import (
    FORMAT,
    build_scene_instance_transform_match,
)


def _sha(char):
    return char * 64


def _draw(draw_order, tx):
    return {
        "draw_order": draw_order,
        "binding_index": 17,
        "world_matrix": [
            1.0, 0.0, 0.0, 0.0,
            0.0, 2.0, 0.0, 0.0,
            0.0, 0.0, 3.0, 0.0,
            tx, 4.0, 5.0, 1.0,
        ],
        "hashes": {
            "draw_identity_sha256": (
                _sha("d") if draw_order == 0 else _sha("e")
            )
        },
    }


def _pipeline(register_rows, *, binding_index=17):
    return {
        "format": "SHIFT.IMBRuntimeCapturePipeline/1",
        "pipeline_ready": True,
        "boundary": {
            "attributed_instance_transform_observation_contract": (
                "selected-strong-variant-vertex-constants-v1"
            ),
        },
        "resource_results": [{
            "attributed_texture_observations": [{
                "binding_index": binding_index,
                "frame": 12,
                "draw_index": 3,
                "status": "observed",
                "constant_state": {
                    "vertex": register_rows,
                    "pixel": {},
                },
                "active_texture_bindings": [],
            }],
        }],
    }


def _registers(matrix, start=20):
    return {
        str(start + row): list(matrix[row * 4:(row + 1) * 4])
        for row in range(4)
    }


def _transpose(matrix):
    return [
        matrix[row + column * 4]
        for row in range(4)
        for column in range(4)
    ]


def test_exact_row_major_world_matrix_resolves_repeated_binding():
    first = _draw(0, 1.0)
    second = _draw(1, 2.0)
    report = build_scene_instance_transform_match(
        {
            "format": "SHIFT.NativeSceneBundle/1",
            "ready": True,
            "draws": [first, second],
        },
        _pipeline(_registers(second["world_matrix"])),
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["repeated_binding_count"] == 1
    assert report["resolved_binding_count"] == 1
    row = report["rows"][0]
    assert row["selected_draw_order"] == 1
    assert row["selected_draw_identity_sha256"] == _sha("e")
    observation = row["observations"][0]
    assert observation["status"] == "matched"
    assert observation["candidate_scene_draw_orders"] == [1]
    assert observation["witnesses"][0]["start_register"] == 20
    assert "row-major" in observation["witnesses"][0]["layouts"]


def test_exact_transposed_world_matrix_is_accepted_without_register_claim():
    first = _draw(0, 1.0)
    second = _draw(1, 2.0)
    report = build_scene_instance_transform_match(
        {
            "format": "SHIFT.NativeSceneBundle/1",
            "ready": True,
            "draws": [first, second],
        },
        _pipeline(
            _registers(_transpose(second["world_matrix"]), start=44)
        ),
    )

    assert report["ready"] is True
    witness = report["rows"][0]["observations"][0]["witnesses"][0]
    assert witness["start_register"] == 44
    assert "transpose" in witness["layouts"]
    assert report["boundary"]["register_semantics_assigned"] is False


def test_identical_scene_world_matrices_remain_ambiguous():
    first = _draw(0, 2.0)
    second = _draw(1, 2.0)
    report = build_scene_instance_transform_match(
        {
            "format": "SHIFT.NativeSceneBundle/1",
            "ready": True,
            "draws": [first, second],
        },
        _pipeline(_registers(first["world_matrix"])),
    )

    assert report["ready"] is False
    assert report["resolved_binding_count"] == 0
    row = report["rows"][0]
    assert row["selected_draw_order"] is None
    assert any(
        "scene-draw-constant-ambiguous:2" in reason
        for reason in row["blocking_reasons"]
    )


def test_missing_exact_constant_window_fails_closed():
    first = _draw(0, 1.0)
    second = _draw(1, 2.0)
    registers = _registers(second["world_matrix"])
    registers["21"][0] = 99.0
    report = build_scene_instance_transform_match(
        {
            "format": "SHIFT.NativeSceneBundle/1",
            "ready": True,
            "draws": [first, second],
        },
        _pipeline(registers),
    )

    assert report["ready"] is False
    assert any(
        "world-matrix-constant-window-not-found" in reason
        for reason in report["blocking_reasons"]
    )


def test_single_instance_binding_needs_no_transform_match():
    report = build_scene_instance_transform_match(
        {
            "format": "SHIFT.NativeSceneBundle/1",
            "ready": True,
            "draws": [_draw(0, 1.0)],
        },
        _pipeline({}),
    )

    assert report["ready"] is True
    assert report["status"] == "not-needed"
    assert report["repeated_binding_count"] == 0


def test_transform_observation_contract_is_required():
    pipeline = _pipeline({})
    pipeline["boundary"] = {}
    report = build_scene_instance_transform_match(
        {
            "format": "SHIFT.NativeSceneBundle/1",
            "ready": True,
            "draws": [_draw(0, 1.0), _draw(1, 2.0)],
        },
        pipeline,
    )

    assert report["ready"] is False
    assert (
        "scene-instance-match:transform-observation-contract-missing"
        in report["blocking_reasons"]
    )
