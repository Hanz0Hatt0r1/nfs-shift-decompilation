from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import bmw_playable_render_resource_identity as gate


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FakeArchive:
    def __init__(self, path: Path, rows: list[tuple[str, int, bytes]]):
        self.path = path
        self.entries = [SimpleNamespace(path=name, index=index) for name, index, _ in rows]
        self._payloads = {(name, index): data for name, index, data in rows}

    def extract_entry(self, entry):
        return self._payloads[(entry.path, entry.index)]

    def close(self):
        pass


def _fixture(tmp_path, monkeypatch, *, duplicate_shader=False):
    primary = tmp_path / "BMW_M3_E36.bff"
    cockpit = tmp_path / "BMW_M3_E36_Cockpit.bff"
    render = tmp_path / "RENDER.bff"
    primary.write_bytes(b"primary-archive")
    cockpit.write_bytes(b"cockpit-archive")
    render.write_bytes(b"render-archive")

    mesh_path = "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb"
    bmt_path = "vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt"
    shader_path = "render/shaders/bodywork.fx"
    dds_path = "render/textures/common_paint.dds"
    mesh = b"mesh"
    bmt = b"material"
    shader = b"shader"
    dds = b"texture"

    primary_rows = [
        (mesh_path, 11, mesh),
        (bmt_path, 12, bmt),
        (dds_path, 13, dds),
    ]
    if duplicate_shader:
        primary_rows.append((shader_path, 14, shader))

    archives = {
        str(primary): FakeArchive(primary, primary_rows),
        str(cockpit): FakeArchive(cockpit, []),
        str(render): FakeArchive(render, [(shader_path, 21, shader)]),
    }
    monkeypatch.setattr(
        gate,
        "BFF",
        lambda path: archives[str(Path(path))],
    )

    admission = {
        "format": "SHIFT.BMWBodyMaterialAdmission/1",
        "ready": True,
        "primitive_results": [{
            "primitive_index": 0,
            "ready": True,
            "slice": {
                "material_bmt": bmt_path,
                "material_binding": {"shader": shader_path},
                "packet": {"mesh": {"ref": mesh_path}},
                "provenance": {
                    "mesh_entry": {
                        "archive": primary.name,
                        "path": mesh_path,
                        "index": 11,
                        "sha256": _sha(mesh),
                    },
                    "material_entry": {
                        "archive": primary.name,
                        "path": bmt_path,
                        "index": 12,
                        "sha256": _sha(bmt),
                    },
                    "shader_source": {
                        "kind": "bff-entry",
                        "archive": render.name,
                        "path": shader_path,
                        "index": 21,
                        "sha256": _sha(shader),
                    },
                    "dds_sources": [{
                        "archive": primary.name,
                        "path": dds_path,
                        "index": 13,
                        "sha256": _sha(dds),
                    }],
                },
            },
        }],
    }
    return admission, {
        "primary": primary,
        "cockpit": cockpit,
        "render": render,
    }


def test_phase654_accepts_only_unique_exact_selected_resources(tmp_path, monkeypatch):
    admission, archives = _fixture(tmp_path, monkeypatch)

    report = gate.build_bmw_playable_render_resource_identity_gate(
        admission,
        archives,
    )

    assert report["format"] == "SHIFT.BMWPlayableRenderResourceIdentityGate/1"
    assert report["ready"] is True
    assert report["blocking_reasons"] == []
    assert report["summary"]["claimed_resource_count"] == 4
    assert report["summary"]["verified_resource_count"] == 4
    assert {row["archive_role"] for row in report["resources"]} == {
        "primary",
        "render",
    }
    assert report["boundary"]["basename_fallback_allowed"] is False
    assert report["boundary"]["first_duplicate_selection_allowed"] is False
    assert report["boundary"]["byte_identical_duplicate_is_semantic_identity"] is False


def test_phase654_rejects_byte_identical_duplicate_exact_shader_occurrence(
    tmp_path,
    monkeypatch,
):
    admission, archives = _fixture(
        tmp_path,
        monkeypatch,
        duplicate_shader=True,
    )

    report = gate.build_bmw_playable_render_resource_identity_gate(
        admission,
        archives,
    )

    assert report["ready"] is False
    assert any(
        "exact-resource-occurrence-count:render/shaders/bodywork.fx:expected=1:observed=2"
        in reason
        for reason in report["blocking_reasons"]
    )


def test_phase654_rejects_shader_basename_substitution(tmp_path, monkeypatch):
    admission, archives = _fixture(tmp_path, monkeypatch)
    admission["primitive_results"][0]["slice"]["material_binding"]["shader"] = (
        "bodywork.fx"
    )

    report = gate.build_bmw_playable_render_resource_identity_gate(
        admission,
        archives,
    )

    assert report["ready"] is False
    assert any(
        "shader:logical-path-mismatch" in reason
        for reason in report["blocking_reasons"]
    )


def test_phase654_rejects_payload_hash_drift(tmp_path, monkeypatch):
    admission, archives = _fixture(tmp_path, monkeypatch)
    admission["primitive_results"][0]["slice"]["provenance"]["material_entry"][
        "sha256"
    ] = "0" * 64

    report = gate.build_bmw_playable_render_resource_identity_gate(
        admission,
        archives,
    )

    assert report["ready"] is False
    assert any(
        "phase654:resource-claim-mismatch:vehicles/bmw_m3_e36/bmw_m3_e36_paint.bmt:payload-sha256-mismatch"
        == reason
        for reason in report["blocking_reasons"]
    )


def test_phase654_rejects_external_shader_file_as_playable_resource_identity(
    tmp_path,
    monkeypatch,
):
    admission, archives = _fixture(tmp_path, monkeypatch)
    admission["primitive_results"][0]["slice"]["provenance"]["shader_source"] = {
        "kind": "external-file",
        "path": str(tmp_path / "bodywork.fx"),
        "sha256": _sha(b"shader"),
    }

    report = gate.build_bmw_playable_render_resource_identity_gate(
        admission,
        archives,
    )

    assert report["ready"] is False
    assert any(
        reason.endswith("shader:external-source-not-admissible")
        for reason in report["blocking_reasons"]
    )


def test_phase654_rejects_claimed_entry_index_substitution(tmp_path, monkeypatch):
    admission, archives = _fixture(tmp_path, monkeypatch)
    admission["primitive_results"][0]["slice"]["provenance"]["mesh_entry"][
        "index"
    ] = 99

    report = gate.build_bmw_playable_render_resource_identity_gate(
        admission,
        archives,
    )

    assert report["ready"] is False
    assert any(
        "phase654:resource-claim-mismatch:vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb:entry-index-mismatch"
        == reason
        for reason in report["blocking_reasons"]
    )
