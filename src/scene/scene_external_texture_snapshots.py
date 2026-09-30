"""Validate exact per-draw external sampler2D snapshot resources."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT = "SHIFT.SceneExternalTextureSnapshotSet/1"
TEXTURE_FORMAT = "SHIFT.ReferenceTexture/1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_sha256(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _safe_relative(value: Any) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def resolve_scene_external_texture_snapshots(
    snapshot_set_path: str | Path,
) -> tuple[dict[str, Any], dict[tuple[int, int], dict[str, Any]]]:
    source_path = Path(snapshot_set_path)
    value = _load(source_path)
    root = source_path.parent

    blockers: list[str] = []
    if value.get("format") != FORMAT:
        blockers.append("scene-external-snapshots:invalid-format")
    if value.get("version") != 1:
        blockers.append("scene-external-snapshots:invalid-version")

    raw_rows = value.get("snapshots")
    if not isinstance(raw_rows, list) or not raw_rows:
        blockers.append("scene-external-snapshots:snapshots-missing")
        raw_rows = []

    normalized: list[dict[str, Any]] = []
    resources: dict[tuple[int, int], dict[str, Any]] = {}
    keys: set[tuple[int, int]] = set()

    for index, raw in enumerate(raw_rows):
        prefix = f"scene-external-snapshots:row-{index}:"
        if not isinstance(raw, Mapping):
            blockers.append(prefix + "invalid")
            continue

        try:
            draw_order = int(raw.get("draw_order"))
            register = int(
                raw.get(
                    "d3d9_sampler_register",
                    raw.get("slot"),
                )
            )
        except (TypeError, ValueError):
            blockers.append(prefix + "identity-invalid")
            continue
        if draw_order < 0:
            blockers.append(prefix + "draw-order-invalid")
        if register < 0 or register > 15:
            blockers.append(prefix + "register-invalid")

        sampler_type = str(raw.get("sampler_type") or "")
        if sampler_type != "sampler2D":
            blockers.append(prefix + "sampler-type-not-2d")
        sampler = str(raw.get("sampler") or raw.get("name") or "").strip()
        if not sampler:
            blockers.append(prefix + "sampler-name-missing")

        draw_identity = _valid_sha256(
            raw.get("scene_draw_identity_sha256")
        )
        if draw_identity is None:
            blockers.append(prefix + "draw-identity-sha256-invalid")

        provenance = raw.get("source_provenance")
        if not isinstance(provenance, Mapping) or not provenance.get("kind"):
            blockers.append(prefix + "source-provenance-missing")
            provenance = {}

        relative = _safe_relative(raw.get("reference_texture_path"))
        expected_sha = _valid_sha256(
            raw.get("reference_texture_sha256")
        )
        image: dict[str, Any] | None = None
        actual_sha: str | None = None
        if relative is None:
            blockers.append(prefix + "reference-texture-path-unsafe")
        elif expected_sha is None:
            blockers.append(prefix + "reference-texture-sha256-invalid")
        else:
            path = root / relative
            if not path.is_file():
                blockers.append(prefix + "reference-texture-missing")
            else:
                actual_sha = _sha256(path)
                if actual_sha != expected_sha:
                    blockers.append(
                        prefix + "reference-texture-sha256-mismatch"
                    )
                else:
                    try:
                        image = _load(path)
                    except (OSError, ValueError, TypeError) as error:
                        blockers.append(
                            prefix
                            + "reference-texture-invalid:"
                            + type(error).__name__
                        )
                    else:
                        if image.get("format") != TEXTURE_FORMAT:
                            blockers.append(
                                prefix + "reference-texture-format-invalid"
                            )
                            image = None
                        elif image.get("pixel_format") != "RGBA8":
                            blockers.append(
                                prefix + "reference-texture-not-rgba8"
                            )
                            image = None

        key = (draw_order, register)
        if key in keys:
            blockers.append(
                prefix
                + f"duplicate-draw-register:{draw_order}:s{register}"
            )
        else:
            keys.add(key)

        row_ready = (
            draw_order >= 0
            and 0 <= register <= 15
            and sampler_type == "sampler2D"
            and bool(sampler)
            and draw_identity is not None
            and bool(provenance)
            and relative is not None
            and expected_sha is not None
            and actual_sha == expected_sha
            and image is not None
            and key not in resources
        )
        normalized.append({
            "draw_order": draw_order,
            "scene_draw_identity_sha256": draw_identity,
            "sampler": sampler,
            "sampler_type": sampler_type,
            "d3d9_sampler_register": register,
            "reference_texture": (
                {
                    "path": relative.as_posix(),
                    "sha256": actual_sha,
                    "format": image.get("format"),
                    "source_format": image.get("source_format"),
                    "width": image.get("width"),
                    "height": image.get("height"),
                }
                if image is not None and relative is not None
                else None
            ),
            "source_provenance": dict(provenance),
            "ready": row_ready,
        })
        if row_ready:
            resources[key] = dict(image)

    blockers = list(dict.fromkeys(blockers))
    ready = bool(normalized) and all(
        row.get("ready") is True for row in normalized
    ) and not blockers
    report = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "source_path": str(source_path),
        "source_sha256": _sha256(source_path),
        "snapshot_count": len(normalized),
        "snapshots": normalized,
        "boundary": {
            "exact_draw_identity_required": True,
            "exact_sampler_name_type_register_required": True,
            "reference_texture_content_hash_required": True,
            "snapshot_authenticity_asserted_by_caller": False,
            "infers_renderer_resource_identity": False,
        },
    }
    if not ready:
        resources = {}
    return report, resources


def validate_scene_external_texture_snapshot_set(
    snapshot_set_path: str | Path,
) -> dict[str, Any]:
    report, _ = resolve_scene_external_texture_snapshots(
        snapshot_set_path
    )
    return report
