"""Validate exact scene-bound external sampler2D snapshots.

Phase 589 keeps renderer-owned snapshots separate from material DDS resources.
A snapshot is admissible only for one exact NativeSceneBundle draw identity,
IMB resource identity, primitive, sampler register and sampler type.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

FORMAT = "SHIFT.NativeSceneExternalSamplerSnapshots/1"
PROVENANCE_FORMAT = "SHIFT.ExternalSamplerSnapshotProvenance/1"
TEXTURE_FORMAT = "SHIFT.ReferenceTexture/1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha_json(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def reference_texture_sha256(value: Mapping[str, Any]) -> str:
    """Return the canonical Phase 589 ReferenceTexture object hash."""
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


def _texture_ready(texture: Mapping[str, Any]) -> bool:
    if texture.get("format") != TEXTURE_FORMAT:
        return False
    try:
        width = int(texture.get("width"))
        height = int(texture.get("height"))
    except (TypeError, ValueError):
        return False
    pixels = texture.get("pixels")
    return (
        width > 0
        and height > 0
        and texture.get("pixel_format") == "RGBA8"
        and isinstance(pixels, list)
        and len(pixels) == width * height * 4
        and all(isinstance(value, int) and 0 <= value <= 255 for value in pixels)
    )


def validate_external_sampler_snapshot_contract(
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
            "external sampler snapshots must be "
            "SHIFT.NativeSceneExternalSamplerSnapshots/1"
        )

    blockers: list[str] = []
    if value.get("version") != 1:
        blockers.append("external-snapshot:unsupported-version")
    rows: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    raw_rows = value.get("snapshots")
    if not isinstance(raw_rows, list):
        raw_rows = []
        blockers.append("external-snapshot:snapshots-not-array")

    for ordinal, raw in enumerate(raw_rows):
        reasons: list[str] = []
        if not isinstance(raw, Mapping):
            blockers.append(f"external-snapshot:{ordinal}:row-invalid")
            continue
        row = dict(raw)
        draw_sha = _sha256(row.get("draw_identity_sha256"))
        if draw_sha is None:
            reasons.append("draw-identity-sha256-invalid")

        resource = row.get("resource")
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
            primitive_index = int(row.get("primitive_index"))
        except (TypeError, ValueError):
            primitive_index = -1
        if primitive_index < 0:
            reasons.append("primitive-index-invalid")

        try:
            register = int(row.get("d3d9_sampler_register"))
        except (TypeError, ValueError):
            register = -1
        if not 0 <= register <= 15:
            reasons.append("sampler-register-invalid")

        sampler_type = str(row.get("sampler_type") or "")
        if sampler_type != "sampler2D":
            reasons.append("sampler-type-not-sampler2D")

        texture = row.get("texture")
        if not isinstance(texture, Mapping) or not _texture_ready(texture):
            reasons.append("texture-invalid")
            texture = {}
        expected_texture_sha = _sha256(row.get("texture_sha256"))
        actual_texture_sha = _sha_json(texture) if texture else None
        if expected_texture_sha is None:
            reasons.append("texture-sha256-invalid")
        elif actual_texture_sha != expected_texture_sha:
            reasons.append("texture-sha256-mismatch")

        provenance = row.get("provenance")
        if not isinstance(provenance, Mapping):
            provenance = {}
            reasons.append("provenance-invalid")
        else:
            if provenance.get("format") != PROVENANCE_FORMAT:
                reasons.append("provenance-format-invalid")
            if not str(provenance.get("source_kind") or ""):
                reasons.append("provenance-source-kind-missing")
            if _sha256(provenance.get("source_sha256")) is None:
                reasons.append("provenance-source-sha256-invalid")

        if reasons:
            blockers.extend(
                f"external-snapshot:{ordinal}:{reason}"
                for reason in reasons
            )
            continue

        key = f"{draw_sha}:s{register}:{sampler_type}"
        if key in index:
            blockers.append(
                f"external-snapshot:{ordinal}:duplicate-draw-register-type"
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
            "d3d9_sampler_register": register,
            "sampler_type": sampler_type,
            "texture_sha256": expected_texture_sha,
            "texture": dict(texture),
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


def resolve_draw_external_sampler2d_snapshots(
    contract: Mapping[str, Any],
    draw: Mapping[str, Any],
    submesh: Mapping[str, Any],
) -> tuple[dict[int, dict[str, Any]], list[str], list[dict[str, Any]]]:
    if contract.get("ready") is not True:
        return {}, ["external-snapshot:contract-not-ready"], []

    draw_sha = _sha256(
        (draw.get("hashes") or {}).get("draw_identity_sha256")
    )
    if draw_sha is None:
        return {}, ["external-snapshot:draw-identity-sha256-invalid"], []

    resource = draw.get("resource")
    resource = resource if isinstance(resource, Mapping) else {}
    primitive_index = draw.get("primitive_index")
    try:
        primitive_index = int(primitive_index)
    except (TypeError, ValueError):
        primitive_index = -1

    resolved: dict[int, dict[str, Any]] = {}
    blockers: list[str] = []
    sources: list[dict[str, Any]] = []
    index = contract.get("index")
    index = index if isinstance(index, Mapping) else {}

    for sampler in submesh.get("external_samplers") or []:
        if not isinstance(sampler, Mapping):
            continue
        sampler_type = str(sampler.get("sampler_type") or "")
        if sampler_type != "sampler2D":
            continue
        register_value = sampler.get(
            "d3d9_sampler_register",
            sampler.get("slot"),
        )
        try:
            register = int(register_value)
        except (TypeError, ValueError):
            continue
        key = f"{draw_sha}:s{register}:{sampler_type}"
        snapshot = index.get(key)
        if not isinstance(snapshot, Mapping):
            continue

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
        if _norm(snapshot_resource.get("path")) != _norm(
            resource.get("path")
        ):
            reasons.append("resource-path-mismatch")
        if str(snapshot_resource.get("sha256") or "").lower() != str(
            resource.get("sha256") or ""
        ).lower():
            reasons.append("resource-sha256-mismatch")
        if snapshot.get("primitive_index") != primitive_index:
            reasons.append("primitive-index-mismatch")
        if reasons:
            blockers.extend(
                f"external-snapshot:s{register}:{reason}"
                for reason in reasons
            )
            continue
        if register in resolved:
            blockers.append(
                f"external-snapshot:s{register}:duplicate-resolved-register"
            )
            continue

        resolved[register] = dict(snapshot["texture"])
        sources.append({
            "snapshot_index": snapshot.get("snapshot_index"),
            "draw_identity_sha256": draw_sha,
            "register": register,
            "sampler_type": sampler_type,
            "texture_sha256": snapshot.get("texture_sha256"),
            "resource": dict(snapshot_resource),
            "primitive_index": primitive_index,
            "provenance": dict(snapshot.get("provenance") or {}),
        })

    return resolved, list(dict.fromkeys(blockers)), sources
