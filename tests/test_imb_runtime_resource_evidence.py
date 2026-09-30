from imb_runtime_resource_evidence import (
    FORMAT,
    build_imb_runtime_resource_evidence_set,
)


def _sha(char):
    return char * 64


def _binding(index, *, path="tracks/silverstone/object.imb", sha=None):
    return {
        "binding_index": index,
        "archive": "Silverstone_Era3_GrandPrix.bff",
        "imb_path": path,
        "imb_entry_index": 100,
        "imb_sha256": sha or _sha("a"),
        "primitive_index": index,
        "draw_range": {
            "first_index": index * 6,
            "index_count": 6,
            "primitive_count": 2,
            "primitive_type": 4,
        },
        "property_descriptors": [
            {"id": "200", "words": [2, 0, 0]},
            {"id": "460", "words": [4, 6, 0]},
        ],
        "material_reference": "materials/test.mtx",
        "shader": "render/shaders/basic_instanced.fx",
        "shader_family": "basicinstanced",
        "hash_target_count": 5,
        "capture_ready": True,
    }


def _target_set(*bindings):
    return {
        "format": "SHIFT.IMBRuntimeShaderTargetSet/1",
        "capture_ready": True,
        "binding_targets": list(bindings),
    }


def test_groups_multiple_primitives_under_exact_imb_identity():
    report = build_imb_runtime_resource_evidence_set(
        _target_set(_binding(0), _binding(1))
    )

    assert report["format"] == FORMAT
    assert report["ready"] is True
    assert report["resource_count"] == 1
    assert report["binding_target_count"] == 2
    assert report["multi_primitive_resource_count"] == 1

    resource = report["resources"][0]
    assert resource["binding_indices"] == [0, 1]
    assert resource["resource_path"] == "tracks/silverstone/object.imb"
    assert resource["resource_sha256"] == _sha("a")
    assert [row["primitive_index"] for row in resource["primitive_bindings"]] == [
        0, 1,
    ]

    adapter = resource["runtime_binding_input"]
    assert adapter["format"] == "SHIFT.IMBRuntimeResourceEvidence/1"
    assert adapter["resource"] == "tracks/silverstone/object.imb"
    assert adapter["resource_sha256"] == _sha("a")
    assert adapter["source"]["source_kind"] == "IMB"
    assert adapter["boundary"]["meb_equivalence"] is False


def test_distinct_resource_sha_is_not_collapsed_by_path():
    report = build_imb_runtime_resource_evidence_set(
        _target_set(
            _binding(0, sha=_sha("a")),
            _binding(1, sha=_sha("b")),
        )
    )

    assert report["ready"] is True
    assert report["resource_count"] == 2
    assert report["multi_primitive_resource_count"] == 0


def test_missing_draw_identity_fails_closed():
    binding = _binding(0)
    binding["draw_range"] = {}
    report = build_imb_runtime_resource_evidence_set(
        _target_set(binding)
    )

    assert report["ready"] is False
    assert report["resource_count"] == 0
    assert (
        "binding-0:draw-range-missing-or-invalid"
        in report["blocking_reasons"]
    )


def test_descriptor_mismatch_for_same_resource_is_blocked():
    first = _binding(0)
    second = _binding(1)
    second["property_descriptors"] = [
        {"id": "200", "words": [2, 0, 0]},
        {"id": "220", "words": [2, 2, 0]},
    ]
    report = build_imb_runtime_resource_evidence_set(
        _target_set(first, second)
    )

    assert report["ready"] is False
    assert report["resource_count"] == 1
    assert (
        "binding-1:resource-descriptor-mismatch"
        in report["blocking_reasons"]
    )


def test_wrong_target_format_is_rejected():
    try:
        build_imb_runtime_resource_evidence_set(
            {"format": "SHIFT.Other/1"}
        )
    except ValueError as error:
        assert "SHIFT.IMBRuntimeShaderTargetSet/1" in str(error)
    else:
        raise AssertionError("invalid target format was accepted")
