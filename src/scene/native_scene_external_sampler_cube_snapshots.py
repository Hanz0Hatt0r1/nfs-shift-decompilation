"""Validate exact scene-bound external samplerCube snapshots.

Phase 592 keeps renderer-owned cube snapshots separate from material DDS
resources. The only admitted cube ABI is the already-proven D3D9 sampler s3
boundary consumed by SHIFT.VulkanCubeTexturePacket/1.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from texture_reference import CUBE_FACES, CUBE_FORMAT, FORMAT as TEXTURE_FORMAT

FORMAT = "SHIFT.NativeSceneExternalSamplerCubeSnapshots/1"
PROVENANCE_FORMAT = "SHIFT.ExternalSamplerSnapshotProvenance/1"
REGISTER = 3


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def reference_cube_sha256(value: Mapping[str, Any]) -> str:
    return _sha_json(value)


def _sha256(value: Any) -> str | None:
    text = str(value or "").lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _face_ready(face: Mapping[str, Any]) -> bool:
    if face.get("format") != TEXTURE_FORMAT:
        return False
    try:
        width = int(face.get("width"))
        height = int(face.get("height"))
    except (TypeError, ValueError):
        return False
    pixels = face.get("pixels")
    return (
        width > 0
        and height > 0
        and face.get("pixel_format") == "RGBA8"
        and isinstance(pixels, list)
        and len(pixels) == width * height * 4
        and all(
            isinstance(value, int) and 0 <= value <= 255
            for value in pixels
        )
    )


def _cube_ready(cube: Mapping[str, Any]) -> bool:
    if cube.get("format") != CUBE_FORMAT:
        return False
    faces = cube.get("faces")
    if not isinstance(faces, Mapping) or set(faces) != set(CUBE_FACES):
        return False
    if not all(
        isinstance(faces[name], Mapping) and _face_ready(faces[name])
        for name in CUBE_FACES
    ):
        return False
    dimensions = {
        (int(faces[name]["width"]), int(faces[name]["height"]))
        for name in CUBE_FACES
    }
    if len(dimensions) != 1:
        return False
    width, height = next(iter(dimensions))
    try:
        cube_width = int(cube.get("width"))
        cube_height = int(cube.get("height"))
    except (TypeError, ValueError):
        return False
    return (
        cube_width == width
        and cube_height == height
        and cube.get("pixel_format") == "RGBA8"
    )


def validate_external_sampler_cube_snapshot_contract(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if value is None:
        return {
            "format": FORMAT,
            "version": 1,
            "status": "absent",
            "ready": True,
            "blocking_reasons": [],
            "snapshot_count": 0,
            "snapshots": [],
            "index": {},
        }
    if value.get("format") != FORMAT:
        raise ValueError(
            "external sampler cube snapshots must be "
            "SHIFT.NativeSceneExternalSamplerCubeSnapshots/1"
        )

    blockers: list[str] = []
    if value.get("version") != 1:
        blockers.append("external-cube-snapshot:unsupported-version")

    rows: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    raw_rows = value.get("snapshots")
    if not isinstance(raw_rows, list):
        raw_rows = []
        blockers.append("external-cube-snapshot:snapshots-not-array")

    for ordinal, raw in enumerate(raw_rows):
        reasons: list[str] = []
        if not isinstance(raw, Mapping):
            blockers.append(
                f"external-cube-snapshot:{ordinal}:row-invalid"
            )
            continue

        draw_sha = _sha256(raw.get("draw_identity_sha256"))
        if draw_sha is None:
            reasons.append("draw-identity-sha256-invalid")

        resource = raw.get("resource")
        if not isinstance(resource, Mapping):
            resource = {}
            reasons.append("resource-invalid")
        resource_sha = _sha256(resource.get("sha256"))
        if not _norm(resource.get("path")):
            reasons.append("resource-path-missing")
        if not str(resource.get("archive") or ""):
            reasons.append("resource-archive-missing")
        if resource_sha is None:
            reasons.append("resource-sha256-invalid")

        try:
            primitive_index = int(raw.get("primitive_index"))
        except (TypeError, ValueError):
            primitive_index = -1
        if primitive_index < 0:
            reasons.append("primitive-index-invalid")

        try:
            register = int(raw.get("d3d9_sampler_register"))
        except (TypeError, ValueError):
            register = -1
        if register != REGISTER:
            reasons.append("sampler-register-not-proven-s3")

        if str(raw.get("sampler_type") or "") != "samplerCube":
            reasons.append("sampler-type-not-samplerCube")

        cube = raw.get("cube")
        if not isinstance(cube, Mapping) or not _cube_ready(cube):
            cube = {}
            reasons.append("cube-invalid")
        expected_cube_sha = _sha256(raw.get("cube_sha256"))
        actual_cube_sha = _sha_json(cube) if cube else None
        if expected_cube_sha is None:
            reasons.append("cube-sha256-invalid")
        elif actual_cube_sha != expected_cube_sha:
            reasons.append("cube-sha256-mismatch")

        provenance = raw.get("provenance")
        if not isinstance(provenance, Mapping):
            provenance = {}
            reasons.append("provenance-invalid")
        else:
            if provenance.get("format") != PROVENANCE_FORMAT:
                reasons.append("provenance-format-invalid")
            if provenance.get("source_kind") != "D3D9_CAPTURE_PPM_CUBE":
                reasons.append("provenance-source-kind-invalid")
            source_sha = _sha256(provenance.get("source_sha256"))
            if source_sha is None:
                reasons.append("provenance-source-sha256-invalid")
            face_sources = provenance.get("face_sources")
            if not isinstance(face_sources, Mapping):
                reasons.append("provenance-face-sources-invalid")
            else:
                if set(face_sources) != set(CUBE_FACES):
                    reasons.append("provenance-face-set-invalid")
                else:
                    face_hashes: dict[str, str] = {}
                    for face_name in CUBE_FACES:
                        face_source = face_sources.get(face_name)
                        face_sha = (
                            _sha256(face_source.get("source_sha256"))
                            if isinstance(face_source, Mapping)
                            else None
                        )
                        if (
                            not isinstance(face_source, Mapping)
                            or face_sha is None
                            or not str(face_source.get("snapshot_path") or "")
                        ):
                            reasons.append(
                                f"provenance-face-{face_name}-invalid"
                            )
                        else:
                            face_hashes[face_name] = face_sha
                    if len(face_hashes) == len(CUBE_FACES):
                        aggregate = hashlib.sha256(
                            json.dumps(
                                face_hashes,
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ).hexdigest()
                        if source_sha != aggregate:
                            reasons.append(
                                "provenance-source-sha256-mismatch"
                            )

        if reasons:
            blockers.extend(
                f"external-cube-snapshot:{ordinal}:{reason}"
                for reason in reasons
            )
            continue

        key = f"{draw_sha}:s{REGISTER}:samplerCube"
        if key in index:
            blockers.append(
                f"external-cube-snapshot:{ordinal}:"
                "duplicate-draw-register-type"
            )
            continue

        normalized = {
            "snapshot_index": ordinal,
            "draw_identity_sha256": draw_sha,
            "resource": {
                "archive": str(resource.get("archive")),
                "path": str(resource.get("path")).replace("\\", "/"),
                "sha256": resource_sha,
            },
            "primitive_index": primitive_index,
            "d3d9_sampler_register": REGISTER,
            "sampler_type": "samplerCube",
            "cube_sha256": expected_cube_sha,
            "cube": dict(cube),
            "provenance": dict(provenance),
        }
        rows.append(normalized)
        index[key] = normalized

    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": list(dict.fromkeys(blockers)),
        "snapshot_count": len(rows),
        "snapshots": rows,
        "index": index,
    }


def resolve_draw_external_sampler_cube_snapshot(
    contract: Mapping[str, Any],
    draw: Mapping[str, Any],
    submesh: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[str], dict[str, Any] | None]:
    if contract.get("ready") is not True:
        return None, ["external-cube-snapshot:contract-not-ready"], None

    cube_samplers = [
        row
        for row in (submesh.get("external_samplers") or [])
        if isinstance(row, Mapping)
        and str(row.get("sampler_type") or "") == "samplerCube"
    ]
    if not cube_samplers:
        return None, [], None
    if len(cube_samplers) != 1:
        return None, [
            f"external-cube-snapshot:s3:declaration-count:{len(cube_samplers)}"
        ], None

    sampler = cube_samplers[0]
    try:
        register = int(
            sampler.get("d3d9_sampler_register", sampler.get("slot", -1))
        )
    except (TypeError, ValueError):
        register = -1
    if register != REGISTER:
        return None, [
            f"external-cube-snapshot:s{register}:unsupported-register"
        ], None

    draw_sha = _sha256(
        (draw.get("hashes") or {}).get("draw_identity_sha256")
    )
    if draw_sha is None:
        return None, [
            "external-cube-snapshot:draw-identity-sha256-invalid"
        ], None

    index = contract.get("index")
    index = index if isinstance(index, Mapping) else {}
    snapshot = index.get(f"{draw_sha}:s{REGISTER}:samplerCube")
    if not isinstance(snapshot, Mapping):
        return None, [], None

    resource = draw.get("resource")
    resource = resource if isinstance(resource, Mapping) else {}
    snapshot_resource = snapshot.get("resource")
    snapshot_resource = (
        snapshot_resource
        if isinstance(snapshot_resource, Mapping)
        else {}
    )
    reasons: list[str] = []
    if str(snapshot_resource.get("archive") or "") != str(
        resource.get("archive") or ""
    ):
        reasons.append("resource-archive-mismatch")
    if _norm(snapshot_resource.get("path")) != _norm(resource.get("path")):
        reasons.append("resource-path-mismatch")
    if str(snapshot_resource.get("sha256") or "").lower() != str(
        resource.get("sha256") or ""
    ).lower():
        reasons.append("resource-sha256-mismatch")
    try:
        primitive_index = int(draw.get("primitive_index"))
    except (TypeError, ValueError):
        primitive_index = -1
    if snapshot.get("primitive_index") != primitive_index:
        reasons.append("primitive-index-mismatch")
    if reasons:
        return None, [
            f"external-cube-snapshot:s{REGISTER}:{reason}"
            for reason in reasons
        ], None

    source = {
        "snapshot_index": snapshot.get("snapshot_index"),
        "draw_identity_sha256": draw_sha,
        "register": REGISTER,
        "sampler_type": "samplerCube",
        "cube_sha256": snapshot.get("cube_sha256"),
        "resource": dict(snapshot_resource),
        "primitive_index": primitive_index,
        "provenance": dict(snapshot.get("provenance") or {}),
    }
    return dict(snapshot["cube"]), [], source
