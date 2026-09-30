from imb_runtime_resource_probe import (
    FORMAT,
    build_imb_runtime_resource_probe,
)


def _sha(char="a"):
    return char * 64


def _target_set(*, binding=None):
    if binding is None:
        binding = {
            "binding_index": 4,
            "archive": "Silverstone_Era3_GrandPrix.bff",
            "imb_path": "tracks/_data/instances/object.imb",
            "imb_entry_index": 120,
            "imb_sha256": _sha(),
            "primitive_index": 0,
            "draw_range": {
                "first_index": 30,
                "index_count": 60,
                "primitive_count": 20,
            },
            "vertex_properties": [
                "200", "460", "220", "130",
            ],
            "shader_family": "basicinstanced",
            "hash_target_count": 6,
            "capture_ready": True,
            "resource_identity_ready": True,
            "draw_range_ready": True,
            "same_instance_match_ready": True,
        }
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "binding_targets": [binding],
    }


def test_probe_is_directly_compatible_with_runtime_resource_input():
    report = build_imb_runtime_resource_probe(
        _target_set(),
        4,
    )

    assert report["format"] == FORMAT
    assert report["status"] == "ready"
    assert report["ready"] is True
    assert report["resource"] == (
        "tracks/_data/instances/object.imb"
    )
    assert report["resource_sha256"] == _sha()
    assert report["draw_range"] == {
        "first_index": 30,
        "index_count": 60,
        "primitive_count": 20,
    }
    assert report["property_descriptors"] == [
        {"id": "200", "words": [2, 0, 0]},
        {"id": "460", "words": [4, 6, 0]},
        {"id": "220", "words": [2, 2, 0]},
        {"id": "130", "words": [1, 3, 0]},
    ]
    assert report["boundary"][
        "usage_ordinal_map_still_required"
    ] is True
    assert report["boundary"]["selects_permutation"] is False


def test_probe_rejects_binding_not_ready_for_same_instance_match():
    binding = dict(_target_set()["binding_targets"][0])
    binding["same_instance_match_ready"] = False
    binding["resource_identity_ready"] = False
    report = build_imb_runtime_resource_probe(
        _target_set(binding=binding),
        4,
    )

    assert report["ready"] is False
    assert report["status"] == "blocked"
    assert report["blocking_reasons"] == [
        "resource-identity:not-ready",
        "same-instance-target:not-ready",
    ]


def test_probe_fails_closed_on_invalid_property_id():
    binding = dict(_target_set()["binding_targets"][0])
    binding["vertex_properties"] = ["200", "future-property"]
    report = build_imb_runtime_resource_probe(
        _target_set(binding=binding),
        4,
    )

    assert report["ready"] is False
    assert report["property_descriptors"] == [
        {"id": "200", "words": [2, 0, 0]},
    ]
    assert report["blocking_reasons"] == [
        "property-descriptors:invalid:future-property"
    ]


def test_probe_requires_unique_binding_index():
    try:
        build_imb_runtime_resource_probe(
            _target_set(),
            99,
        )
    except ValueError as error:
        assert "resolves to 0 rows" in str(error)
    else:
        raise AssertionError("missing binding index was accepted")


def test_probe_rejects_wrong_target_format():
    try:
        build_imb_runtime_resource_probe(
            {"format": "SHIFT.Other/1"},
            0,
        )
    except ValueError as error:
        assert "SHIFT.IMBRuntimeShaderTargetSet/1" in str(error)
    else:
        raise AssertionError("wrong target format was accepted")
