import json
from pathlib import Path

import bmw_body_material_admission as admission


def _golden(tmp_path, count=3):
    path = tmp_path / "golden.json"
    path.write_text(
        json.dumps({
            "format": "SHIFT.BMWGoldenAssetManifest/1",
            "golden": {
                "resource": (
                    "vehicles/bmw_m3_e36/"
                    "bmw_m3_e36_kit00_body_loda.meb"
                ),
                "resource_sha256": "a" * 64,
            },
            "mesh": {
                "primitives": [
                    {
                        "first_index": index * 3,
                        "index_count": 3,
                        "material": (
                            "vehicles/bmw_m3_e36/"
                            f"MATERIAL_{index}.mtx"
                        ),
                    }
                    for index in range(count)
                ],
            },
        }),
        encoding="utf-8",
    )
    return path


def _slice(index, *, ready=True, permutation=None, reasons=None):
    identity = permutation or chr(ord("a") + index) * 64
    return {
        "format": "SHIFT.BMWMaterialSlice/1",
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(reasons or []),
        "primitive_index": index,
        "material_ref": (
            "vehicles/bmw_m3_e36/"
            f"MATERIAL_{index}.mtx"
        ),
        "material_bmt": (
            "vehicles/bmw_m3_e36/"
            f"MATERIAL_{index}.bmt"
        ),
        "material_binding": {
            "permutation_identity": {
                "format": "SHIFT.ShaderPermutationIdentity/1",
                "identity_sha256": identity,
            },
        },
        "render_command": {
            "format": "SHIFT.RenderCommand/1",
            "ready": ready,
            "submeshes": [{
                "shader": {
                    "permutation_identity": {
                        "format": "SHIFT.ShaderPermutationIdentity/1",
                        "identity_sha256": identity,
                    },
                },
            }],
        },
    }


def test_body_admission_runs_all_canonical_primitives_and_groups_permutations(
    monkeypatch, tmp_path
):
    golden = _golden(tmp_path)
    shared = "f" * 64
    by_index = {
        0: _slice(0, permutation=shared),
        1: _slice(1, permutation="e" * 64),
        2: _slice(2, permutation=shared),
    }
    seen = []

    def fake_slice(primary, golden_path, **kwargs):
        index = kwargs["primitive_index"]
        seen.append(index)
        return by_index[index]

    monkeypatch.setattr(
        admission,
        "build_real_bmw_material_slice",
        fake_slice,
    )
    monkeypatch.setattr(
        admission,
        "build_bmw_material_slice_set",
        lambda slices: {
            "format": "SHIFT.BMWMaterialSliceSet/1",
            "ready": True,
            "blocking_reasons": [],
            "draw_count": len(slices),
        },
    )

    result = admission.build_bmw_body_material_admission(
        tmp_path / "BMW_M3_E36.bff",
        golden,
    )

    assert seen == [0, 1, 2]
    assert result["ready"] is True
    assert result["status"] == "ready"
    assert result["admission"]["ready_primitive_count"] == 3
    assert result["admission"]["blocked_primitive_count"] == 0
    assert result["admission"]["distinct_ready_permutation_count"] == 2
    shared_row = next(
        row
        for row in result["admission"]["permutations"]
        if row["identity_sha256"] == shared
    )
    assert shared_row["primitive_indices"] == [0, 2]
    assert shared_row["primitive_count"] == 2


def test_body_admission_preserves_ready_subset_when_other_primitives_block(
    monkeypatch, tmp_path
):
    golden = _golden(tmp_path)
    ready = _slice(0)
    blocked = _slice(
        1,
        ready=False,
        reasons=["generic-material:shader-selection-not-unique"],
    )
    set_inputs = []

    def fake_slice(primary, golden_path, **kwargs):
        index = kwargs["primitive_index"]
        if index == 0:
            return ready
        if index == 1:
            return blocked
        raise RuntimeError("missing retail FXO")

    def fake_set(slices):
        set_inputs.extend(slices)
        return {
            "format": "SHIFT.BMWMaterialSliceSet/1",
            "ready": True,
            "blocking_reasons": [],
            "draw_count": len(slices),
        }

    monkeypatch.setattr(
        admission,
        "build_real_bmw_material_slice",
        fake_slice,
    )
    monkeypatch.setattr(
        admission,
        "build_bmw_material_slice_set",
        fake_set,
    )

    result = admission.build_bmw_body_material_admission(
        tmp_path / "BMW_M3_E36.bff",
        golden,
    )

    assert result["ready"] is False
    assert result["status"] == "partial"
    assert result["admission"]["ready_primitive_indices"] == [0]
    assert result["admission"]["blocked_primitive_indices"] == [1, 2]
    assert set_inputs == [ready]
    assert (
        "body-admission:primitive-1:"
        "generic-material:shader-selection-not-unique"
        in result["blocking_reasons"]
    )
    assert any(
        reason.startswith(
            "body-admission:primitive-2:RuntimeError:"
        )
        for reason in result["blocking_reasons"]
    )


def test_body_admission_forwards_ready_set_to_vulkan_adapter(
    monkeypatch, tmp_path
):
    golden = _golden(tmp_path, count=2)
    calls = {}

    monkeypatch.setattr(
        admission,
        "build_real_bmw_material_slice",
        lambda primary, golden_path, **kwargs: _slice(
            kwargs["primitive_index"]
        ),
    )
    slice_set = {
        "format": "SHIFT.BMWMaterialSliceSet/1",
        "ready": True,
        "blocking_reasons": [],
        "draw_count": 2,
    }
    monkeypatch.setattr(
        admission,
        "build_bmw_material_slice_set",
        lambda slices: slice_set,
    )

    def fake_vulkan(payload, output_dir, *, source_bffs):
        calls["payload"] = payload
        calls["output_dir"] = Path(output_dir)
        calls["source_bffs"] = [Path(path).name for path in source_bffs]
        return {
            "format": "SHIFT.BMWMaterialSliceVulkanSet/1",
            "ready": True,
            "blocking_reasons": [],
            "draw_count": 2,
        }

    monkeypatch.setattr(
        admission,
        "build_bmw_vulkan_set_from_material_slice",
        fake_vulkan,
    )

    result = admission.build_bmw_body_material_admission(
        tmp_path / "BMW_M3_E36.bff",
        golden,
        supplemental_bffs=[
            tmp_path / "BMW_M3_E36_Cockpit.bff",
            tmp_path / "RENDER.bff",
        ],
        vulkan_output_dir=tmp_path / "vulkan",
    )

    assert result["ready"] is True
    assert result["vulkan_set"]["ready"] is True
    assert calls["payload"] is slice_set
    assert calls["output_dir"] == tmp_path / "vulkan"
    assert calls["source_bffs"] == [
        "BMW_M3_E36.bff",
        "BMW_M3_E36_Cockpit.bff",
        "RENDER.bff",
    ]


def test_body_admission_blocks_when_vulkan_handoff_blocks(
    monkeypatch, tmp_path
):
    golden = _golden(tmp_path, count=1)
    monkeypatch.setattr(
        admission,
        "build_real_bmw_material_slice",
        lambda *args, **kwargs: _slice(0),
    )
    monkeypatch.setattr(
        admission,
        "build_bmw_material_slice_set",
        lambda slices: {
            "format": "SHIFT.BMWMaterialSliceSet/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(
        admission,
        "build_bmw_vulkan_set_from_material_slice",
        lambda *args, **kwargs: {
            "format": "SHIFT.BMWMaterialSliceVulkanSet/1",
            "ready": False,
            "blocking_reasons": [
                "native-submission:shader-payload-identity-missing"
            ],
        },
    )

    result = admission.build_bmw_body_material_admission(
        tmp_path / "BMW_M3_E36.bff",
        golden,
        vulkan_output_dir=tmp_path / "vulkan",
    )

    assert result["ready"] is False
    assert result["status"] == "partial"
    assert (
        "body-admission:vulkan-set:"
        "native-submission:shader-payload-identity-missing"
        in result["blocking_reasons"]
    )


def test_body_admission_rejects_duplicate_or_out_of_range_selection(tmp_path):
    golden = _golden(tmp_path, count=2)

    try:
        admission.build_bmw_body_material_admission(
            tmp_path / "BMW_M3_E36.bff",
            golden,
            primitive_indices=[0, 0],
        )
    except ValueError as error:
        assert "unique" in str(error)
    else:
        raise AssertionError("duplicate primitive indices must be rejected")

    try:
        admission.build_bmw_body_material_admission(
            tmp_path / "BMW_M3_E36.bff",
            golden,
            primitive_indices=[2],
        )
    except ValueError as error:
        assert "out of range" in str(error)
    else:
        raise AssertionError("out-of-range primitive must be rejected")


def test_body_admission_writer_persists_slices_set_and_report(
    monkeypatch, tmp_path
):
    golden = _golden(tmp_path, count=1)
    material_slice = _slice(0)
    monkeypatch.setattr(
        admission,
        "build_real_bmw_material_slice",
        lambda *args, **kwargs: material_slice,
    )
    monkeypatch.setattr(
        admission,
        "build_bmw_material_slice_set",
        lambda slices: {
            "format": "SHIFT.BMWMaterialSliceSet/1",
            "ready": True,
            "blocking_reasons": [],
        },
    )
    report = admission.build_bmw_body_material_admission(
        tmp_path / "BMW_M3_E36.bff",
        golden,
    )

    output = admission.write_bmw_body_material_admission(
        report,
        tmp_path / "out",
    )

    assert output == tmp_path / "out" / "admission.json"
    assert output.is_file()
    assert (tmp_path / "out" / "material_slice_set.json").is_file()
    persisted_slice = json.loads(
        (tmp_path / "out" / "slices" / "primitive_00.json")
        .read_text(encoding="utf-8")
    )
    assert persisted_slice["primitive_index"] == 0
