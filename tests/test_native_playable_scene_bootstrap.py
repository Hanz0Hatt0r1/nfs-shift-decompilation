from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path

import native_playable_scene_bootstrap as mod
from offline_resource_pipeline import MaterializedArchive


def _rows(tmp_path: Path, names: list[str]) -> list[MaterializedArchive]:
    rows: list[MaterializedArchive] = []
    for index, name in enumerate(names):
        path = tmp_path / f"src_{index}" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode("ascii"))
        rows.append(MaterializedArchive(str(path.parent), None, path))
    return rows


def _patch_materialize(monkeypatch, rows):
    @contextmanager
    def fake_materialize(inputs):
        assert list(inputs) == ["Vehicles.zip", "SHIFT_tail.zip"]
        yield rows

    monkeypatch.setattr(mod, "materialize_bff_inputs", fake_materialize)


def _ready_admission():
    return {
        "format": "SHIFT.BMWBodyMaterialAdmission/1",
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "material_slice_set": {
            "format": "SHIFT.BMWMaterialSliceSet/1",
            "ready": True,
        },
    }


def _ready_vhf_transform():
    return {
        "format": "SHIFT.BMWVHFBodyWorldTransform/1",
        "ready": True,
        "status": "ready",
        "blocking_reasons": [],
        "source": {
            "mesh_resource": "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
            "mesh_sha256": "d" * 64,
        },
        "world_matrix": [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            1.0, 2.0, 3.0, 1.0,
        ],
    }


def test_corpus_bootstrap_selects_exact_archives_builds_vhf_transform_and_phase643(
    monkeypatch,
    tmp_path,
):
    rows = _rows(
        tmp_path,
        ["BMW_M3_E36.bff", "BMW_M3_E36_Cockpit.bff", "RENDER.bff"],
    )
    _patch_materialize(monkeypatch, rows)
    admission_calls = []
    transform_calls = []
    apply_calls = []
    composition_calls = []

    def admission(primary, golden, *, supplemental_bffs):
        admission_calls.append(
            (Path(primary), Path(golden), [Path(x) for x in supplemental_bffs])
        )
        return _ready_admission()

    def write_admission(report, output_dir):
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        (root / "material_slice_set.json").write_text(
            json.dumps({
                "format": "SHIFT.BMWMaterialSliceSet/1",
                "ready": True,
                "render_command": {"world_matrix": None},
            }),
            encoding="utf-8",
        )
        path = root / "admission.json"
        path.write_text(
            '{"format":"SHIFT.BMWBodyMaterialAdmission/1","ready":true}\n',
            encoding="utf-8",
        )
        return path

    def build_transform(primary, golden):
        transform_calls.append((Path(primary), Path(golden)))
        return _ready_vhf_transform()

    def apply_transform(source, transform):
        apply_calls.append((Path(source), transform))
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
        payload["render_command"]["world_matrix"] = transform["world_matrix"]
        payload["vhf_body_world_transform"] = transform
        return payload

    def compose(track, material_slice, output_dir, **kwargs):
        composition_calls.append((Path(track), Path(material_slice), kwargs))
        payload = json.loads(Path(material_slice).read_text(encoding="utf-8"))
        assert payload["render_command"]["world_matrix"] == _ready_vhf_transform()["world_matrix"]
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        (root / "playable_scene_composition.json").write_text("{}\n", encoding="utf-8")
        return {
            "format": "SHIFT.NativePlayableSceneVulkanSet/1",
            "ready": True,
            "status": "ready",
            "blocking_reasons": [],
        }

    monkeypatch.setattr(mod, "build_bmw_body_material_admission", admission)
    monkeypatch.setattr(mod, "write_bmw_body_material_admission", write_admission)
    monkeypatch.setattr(mod, "build_bmw_vhf_body_world_transform", build_transform)
    monkeypatch.setattr(mod, "apply_bmw_vhf_body_world_transform", apply_transform)
    monkeypatch.setattr(mod, "build_native_playable_scene_vulkan_set", compose)

    track = tmp_path / "track-scene"
    track.mkdir()
    out = tmp_path / "playable"
    report = mod.build_native_playable_scene_bootstrap(
        ["Vehicles.zip", "SHIFT_tail.zip"],
        track,
        out,
        vehicle="BMW_M3_E36",
        validator="glslangValidator",
    )

    assert report["format"] == mod.FORMAT
    assert report["ready"] is True
    assert report["scene_set_ready"] is True
    assert report["blocking_reasons"] == []
    assert report["archive_sources"]["primary"]["archive"] == "BMW_M3_E36.bff"
    assert report["archive_sources"]["cockpit"]["archive"] == "BMW_M3_E36_Cockpit.bff"
    assert report["archive_sources"]["render"]["archive"] == "RENDER.bff"

    primary, _, supplemental = admission_calls[0]
    assert primary.name == "BMW_M3_E36.bff"
    assert [path.name for path in supplemental] == [
        "BMW_M3_E36_Cockpit.bff",
        "RENDER.bff",
    ]
    assert transform_calls[0][0].name == "BMW_M3_E36.bff"
    assert apply_calls[0][0].name == "material_slice_set.json"
    assert composition_calls[0][1].name == (
        "vehicle-material-slice-set-with-vhf-transform.json"
    )
    assert [Path(path).name for path in composition_calls[0][2]["source_bffs"]] == [
        "BMW_M3_E36.bff",
        "BMW_M3_E36_Cockpit.bff",
        "RENDER.bff",
    ]
    assert composition_calls[0][2]["validator"] == "glslangValidator"

    assert report["boundary"]["phase645_vhf_body_world_transform_required"] is True
    assert report["boundary"]["vhf_body_world_transform_consumed"] is True
    assert report["boundary"]["phase643_composite_scene_consumed"] is True
    assert report["boundary"]["phase700_runtime_pose_handoff_consumed"] is False
    assert Path(report["artifacts"]["vehicle_vhf_body_world_transform"]).is_file()
    assert Path(
        report["artifacts"]["vehicle_material_slice_set_with_vhf_transform"]
    ).is_file()


def test_corpus_bootstrap_blocks_when_required_render_archive_is_missing(
    monkeypatch,
    tmp_path,
):
    rows = _rows(tmp_path, ["BMW_M3_E36.bff", "BMW_M3_E36_Cockpit.bff"])
    _patch_materialize(monkeypatch, rows)

    def forbidden(*args, **kwargs):
        raise AssertionError("material admission must not run with missing RENDER.bff")

    monkeypatch.setattr(mod, "build_bmw_body_material_admission", forbidden)
    track = tmp_path / "track-scene"
    track.mkdir()
    report = mod.build_native_playable_scene_bootstrap(
        ["Vehicles.zip", "SHIFT_tail.zip"],
        track,
        tmp_path / "playable",
        vehicle="BMW_M3_E36",
    )

    assert report["ready"] is False
    assert report["scene_set_ready"] is False
    assert "playable-scene-corpus:archive-missing:RENDER.bff" in report["blocking_reasons"]


def test_corpus_bootstrap_blocks_when_vhf_transform_cannot_be_proven(
    monkeypatch,
    tmp_path,
):
    rows = _rows(
        tmp_path,
        ["BMW_M3_E36.bff", "BMW_M3_E36_Cockpit.bff", "RENDER.bff"],
    )
    _patch_materialize(monkeypatch, rows)

    monkeypatch.setattr(mod, "build_bmw_body_material_admission", lambda *a, **k: _ready_admission())

    def write_admission(report, output_dir):
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        (root / "material_slice_set.json").write_text(
            '{"format":"SHIFT.BMWMaterialSliceSet/1","ready":true}\n',
            encoding="utf-8",
        )
        return root / "admission.json"

    monkeypatch.setattr(mod, "write_bmw_body_material_admission", write_admission)
    monkeypatch.setattr(
        mod,
        "build_bmw_vhf_body_world_transform",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("canonical VHF body mismatch")),
    )

    def forbidden_compose(*args, **kwargs):
        raise AssertionError("Phase 643 must not run without proven VHF body transform")

    monkeypatch.setattr(mod, "build_native_playable_scene_vulkan_set", forbidden_compose)

    track = tmp_path / "track-scene"
    track.mkdir()
    report = mod.build_native_playable_scene_bootstrap(
        ["Vehicles.zip", "SHIFT_tail.zip"],
        track,
        tmp_path / "playable",
        vehicle="BMW_M3_E36",
    )

    assert report["ready"] is False
    assert any(
        reason.startswith("playable-scene-bootstrap:vehicle-vhf-transform-failed:ValueError")
        for reason in report["blocking_reasons"]
    )
    assert report["boundary"]["vhf_body_world_transform_consumed"] is False


def test_corpus_bootstrap_rejects_duplicate_canonical_archive_basename(
    monkeypatch,
    tmp_path,
):
    rows = _rows(
        tmp_path,
        [
            "BMW_M3_E36.bff",
            "BMW_M3_E36_Cockpit.bff",
            "RENDER.bff",
            "RENDER.bff",
        ],
    )
    _patch_materialize(monkeypatch, rows)
    track = tmp_path / "track-scene"
    track.mkdir()
    report = mod.build_native_playable_scene_bootstrap(
        ["Vehicles.zip", "SHIFT_tail.zip"],
        track,
        tmp_path / "playable",
        vehicle="BMW_M3_E36",
    )

    assert report["ready"] is False
    assert "playable-scene-corpus:archive-ambiguous:RENDER.bff:2" in report["blocking_reasons"]
    assert report["boundary"]["archive_order_is_selection_authority"] is False


def test_corpus_bootstrap_rejects_noncanonical_vehicle_before_archive_selection(
    monkeypatch,
    tmp_path,
):
    def forbidden_materialize(*args, **kwargs):
        raise AssertionError("unsupported vehicle must fail before corpus materialization")

    monkeypatch.setattr(mod, "materialize_bff_inputs", forbidden_materialize)
    track = tmp_path / "track-scene"
    track.mkdir()
    report = mod.build_native_playable_scene_bootstrap(
        ["Vehicles.zip", "SHIFT_tail.zip"],
        track,
        tmp_path / "playable",
        vehicle="FORD_MUSTANG_2010",
    )

    assert report["ready"] is False
    assert report["blocking_reasons"] == [
        "playable-scene-bootstrap:unsupported-vehicle:FORD_MUSTANG_2010"
    ]
