"""Join offline BFF resource evidence to existing native scene/physics gates.

This module does not create runtime evidence. It only proves that already-proven
native scene draws and parsed vehicle physics resources point back to exact
entries in SHIFT.OfflineResourceCatalog/1 / SHIFT.SceneVehicleBootstrap/1.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

CATALOG_FORMAT = "SHIFT.OfflineResourceCatalog/1"
BOOTSTRAP_FORMAT = "SHIFT.SceneVehicleBootstrap/1"
PHYSICS_BUNDLE_FORMAT = "SHIFT.VehiclePhysicsBundleExtractor/1"
PHYSICS_GRAPH_FORMAT = "SHIFT.VehiclePhysicsAssetGraph/1"
SCENE_SET_FORMAT = "SHIFT.NativeSceneVulkanSet/1"
SCENE_PREPARE_FORMAT = "SHIFT.NativeSceneVulkanSetPrepare/1"
SCENE_JOIN_FORMAT = "SHIFT.OfflineSceneCatalogJoin/1"
PHYSICS_MANIFEST_FORMAT = "SHIFT.VehiclePhysicsResourceManifest/1"
BMW_COMPAT_FORMAT = "SHIFT.BMWM3VehiclePhysicsResourceManifest/1"
HANDOFF_FORMAT = "SHIFT.OfflineNativeResourceHandoff/1"

PHYSICS_KINDS = ("cdf", "edf", "gdf", "sdf", "tbf", "bbf")
RUNTIME_PHYSICS_KINDS = ("cdf", "edf", "gdf", "sdf")


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _sha(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_archive(bootstrap: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    selected = bootstrap.get("selected_archives") or {}
    row = selected.get(key) if isinstance(selected, Mapping) else None
    return row if isinstance(row, Mapping) else None


def _catalog_by_id(catalog: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("id")): row
        for row in (catalog.get("resources") or [])
        if isinstance(row, Mapping) and row.get("id")
    }


def _int_field(value: Any, *, name: str, minimum: int = 0) -> tuple[int | None, str | None]:
    if isinstance(value, bool):
        return None, f"{name}:invalid"
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None, f"{name}:missing-or-invalid"
    if number < minimum:
        return None, f"{name}:below-minimum:{minimum}"
    return number, None


def build_vehicle_physics_resource_manifest(
    catalog: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    physics_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a neutral exact-entry physics manifest from Process D outputs."""
    blockers: list[str] = []
    if catalog.get("format") != CATALOG_FORMAT:
        blockers.append("catalog:invalid-format")
    if bootstrap.get("format") != BOOTSTRAP_FORMAT:
        blockers.append("bootstrap:invalid-format")
    if bootstrap.get("ready") is not True:
        blockers.append("bootstrap:not-ready")
    if physics_bundle.get("format") != PHYSICS_BUNDLE_FORMAT:
        blockers.append("physics-bundle:invalid-format")
    if physics_bundle.get("ready") is not True:
        blockers.append("physics-bundle:not-ready")

    vehicle_archive = _selected_archive(bootstrap, "vehicle")
    if vehicle_archive is None:
        blockers.append("vehicle-archive:missing")
        vehicle_archive = {}

    source = physics_bundle.get("source") or {}
    source_name = Path(str(source.get("bff") or "")).name
    archive_name = str(vehicle_archive.get("archive_name") or "")
    if not source_name or source_name.lower() != archive_name.lower():
        blockers.append("physics-bundle:source-archive-mismatch")

    roots = (bootstrap.get("roots") or {}).get("vehicle") or {}
    if not isinstance(roots, Mapping):
        roots = {}
        blockers.append("bootstrap:vehicle-roots-missing")
    bundle_entries = physics_bundle.get("entries") or {}
    if not isinstance(bundle_entries, Mapping):
        bundle_entries = {}
        blockers.append("physics-bundle:entries-missing")

    resources = _catalog_by_id(catalog)
    profile = physics_bundle.get("profile") or {}
    if not isinstance(profile, Mapping) or profile.get("format") != PHYSICS_GRAPH_FORMAT:
        blockers.append("physics-profile:invalid-format")
        profile = {}
    if profile.get("ready") is not True:
        blockers.append("physics-profile:not-ready")
    profile_resources = profile.get("resources") or {}
    if not isinstance(profile_resources, Mapping):
        profile_resources = {}
    summary = profile.get("summary") or {}
    if not isinstance(summary, Mapping):
        summary = {}

    entries: dict[str, dict[str, Any]] = {}
    for kind in PHYSICS_KINDS:
        root_id = roots.get("." + kind)
        if not isinstance(root_id, str) or not root_id:
            blockers.append(f"{kind}:bootstrap-root-missing")
            continue
        row = resources.get(root_id)
        if row is None:
            blockers.append(f"{kind}:catalog-resource-missing")
            continue
        if str(row.get("archive_id") or "") != str(vehicle_archive.get("id") or ""):
            blockers.append(f"{kind}:catalog-archive-mismatch")

        entry = bundle_entries.get(kind)
        if not isinstance(entry, Mapping):
            blockers.append(f"{kind}:physics-bundle-entry-missing")
            continue

        structural_pairs = (
            ("path", _norm(row.get("path")), _norm(entry.get("archive_path"))),
            ("index", row.get("index"), entry.get("index")),
            ("type", row.get("compression_type"), entry.get("type")),
            ("compressed_size", row.get("compressed_size"), entry.get("compressed_size")),
            ("uncompressed_size", row.get("uncompressed_size"), entry.get("uncompressed_size")),
        )
        for label, expected, actual in structural_pairs:
            if expected != actual:
                blockers.append(f"{kind}:catalog-{label}-mismatch")

        decoded_sha = _sha(entry.get("decoded_sha256"))
        raw_sha = _sha(entry.get("raw_sha256"))
        if decoded_sha is None:
            blockers.append(f"{kind}:decoded-sha256-missing-or-invalid")
        if raw_sha is None:
            blockers.append(f"{kind}:raw-sha256-missing-or-invalid")

        profile_resource = profile_resources.get(kind)
        if kind in RUNTIME_PHYSICS_KINDS:
            if not isinstance(profile_resource, Mapping):
                blockers.append(f"{kind}:profile-resource-missing")
            elif decoded_sha is not None and _sha(profile_resource.get("sha256")) != decoded_sha:
                blockers.append(f"{kind}:profile-sha256-mismatch")

        entries[kind] = {
            "resource_id": root_id,
            "path": row.get("path"),
            "entry_index": row.get("index"),
            "type": row.get("compression_type"),
            "compressed_size": row.get("compressed_size"),
            "uncompressed_size": row.get("uncompressed_size"),
            "decoded_sha256": decoded_sha,
            "raw_sha256": raw_sha,
        }

    body_count, body_error = _int_field(summary.get("sdf_bodies"), name="body-count", minimum=1)
    joint_count, joint_error = _int_field(summary.get("sdf_joint_hinge_count"), name="joint-hinge-count")
    bar_count, bar_error = _int_field(summary.get("sdf_bar_count"), name="bar-count")
    for error in (body_error, joint_error, bar_error):
        if error:
            blockers.append(error)

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers and len(entries) == len(PHYSICS_KINDS)
    return {
        "format": PHYSICS_MANIFEST_FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "vehicle": bootstrap.get("vehicle"),
        "source_archive": archive_name or None,
        "source_archive_id": vehicle_archive.get("id"),
        "entries": entries,
        "body_count": body_count,
        "joint_hinge_count": joint_count,
        "bar_count": bar_count,
        "source": {
            "catalog_format": catalog.get("format"),
            "bootstrap_format": bootstrap.get("format"),
            "physics_bundle_format": physics_bundle.get("format"),
            "physics_profile_format": profile.get("format") if isinstance(profile, Mapping) else None,
        },
        "boundary": {
            "entry_identity": "exact-archive-id/path/index/type/sizes",
            "payload_identity": "physics-bundle-decoded/raw-sha256",
            "profile_payload_join": "cdf/edf/gdf/sdf exact decoded-sha256",
            "runtime_provider_identity_claimed": False,
            "runtime_schedule_claimed": False,
            "missing_resource_synthesis": False,
        },
    }


def build_bmw_m3_runtime_compat_manifest(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Emit the current native_runtime-compatible BMW manifest when exact."""
    blockers: list[str] = []
    if manifest.get("format") != PHYSICS_MANIFEST_FORMAT:
        blockers.append("vehicle-physics-manifest:invalid-format")
    if manifest.get("ready") is not True:
        blockers.append("vehicle-physics-manifest:not-ready")
    if str(manifest.get("source_archive") or "").lower() != "bmw_m3_e36.bff":
        blockers.append("native-runtime-currently-accepts-bmw-m3-e36-only")

    entries = manifest.get("entries") or {}
    archive_entry_points: list[dict[str, Any]] = []
    for kind in RUNTIME_PHYSICS_KINDS:
        row = entries.get(kind) if isinstance(entries, Mapping) else None
        if not isinstance(row, Mapping):
            blockers.append(f"{kind}:manifest-entry-missing")
            continue
        decoded_sha = _sha(row.get("decoded_sha256"))
        if decoded_sha is None:
            blockers.append(f"{kind}:decoded-sha256-missing-or-invalid")
        archive_entry_points.append({
            "path": row.get("path"),
            "entry_index": row.get("entry_index"),
            "compressed_size": row.get("compressed_size"),
            "uncompressed_size": row.get("uncompressed_size"),
            "type": row.get("type"),
            "sha256": decoded_sha,
        })

    body_count = manifest.get("body_count")
    joint_count = manifest.get("joint_hinge_count")
    bar_count = manifest.get("bar_count")
    for label, value in (
        ("body_count", body_count),
        ("joint_hinge_count", joint_count),
        ("bar_count", bar_count),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            blockers.append(f"{label}:missing-or-invalid")

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    def entry_sha(kind: str) -> str | None:
        row = entries.get(kind) if isinstance(entries, Mapping) else None
        return _sha(row.get("decoded_sha256")) if isinstance(row, Mapping) else None

    return {
        "format": BMW_COMPAT_FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "source_archive": manifest.get("source_archive"),
        "archive_entry_points": archive_entry_points,
        "body_count": body_count,
        "joint_hinge_count": joint_count,
        "bar_count": bar_count,
        "cdf": {"sha256": entry_sha("cdf")},
        "edf": {"sha256": entry_sha("edf")},
        "gdf": {"sha256": entry_sha("gdf")},
        "sdf": {
            "sha256": entry_sha("sdf"),
            "body_count": body_count,
            "joint_hinge_count": joint_count,
            "bar_count": bar_count,
        },
        "policy": {
            "generated_from_offline_resource_pipeline": True,
            "binary_content_committed": False,
            "retail_text_content_committed": False,
            "identity_and_structure_only": True,
        },
    }


def build_scene_catalog_join(
    catalog: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    scene_set: Mapping[str, Any] | None,
    scene_prepare: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Join runtime-proven scene-set IMB identities to exact catalog entries."""
    blockers: list[str] = []
    if catalog.get("format") != CATALOG_FORMAT:
        blockers.append("catalog:invalid-format")
    if bootstrap.get("format") != BOOTSTRAP_FORMAT:
        blockers.append("bootstrap:invalid-format")
    if bootstrap.get("ready") is not True:
        blockers.append("bootstrap:not-ready")

    track_archive = _selected_archive(bootstrap, "track_visual")
    if track_archive is None:
        blockers.append("track-visual-archive:missing")
        track_archive = {}

    if not isinstance(scene_set, Mapping):
        blockers.append("scene-set:runtime-proven-input-required")
        scene_set = {}
    elif scene_set.get("format") != SCENE_SET_FORMAT:
        blockers.append("scene-set:invalid-format")
    elif scene_set.get("ready") is not True:
        blockers.append("scene-set:not-ready")

    if scene_prepare is not None:
        if scene_prepare.get("format") != SCENE_PREPARE_FORMAT:
            blockers.append("scene-prepare:invalid-format")
        elif scene_prepare.get("ready") is not True:
            blockers.append("scene-prepare:not-ready")

    resources = [
        row for row in (catalog.get("resources") or [])
        if isinstance(row, Mapping)
    ]
    joined: list[dict[str, Any]] = []
    draws = [
        row for row in (scene_set.get("draws") or [])
        if isinstance(row, Mapping)
    ]
    expected_count = scene_set.get("draw_count")
    if scene_set and expected_count != len(draws):
        blockers.append("scene-set:draw-count-mismatch")

    selected_archive_id = str(track_archive.get("id") or "")
    selected_archive_name = str(track_archive.get("archive_name") or "")
    for index, draw in enumerate(draws):
        draw_blockers: list[str] = []
        if draw.get("ready") is not True:
            draw_blockers.append("draw:not-ready")
        try:
            draw_order = int(draw.get("draw_order"))
        except (TypeError, ValueError):
            draw_order = -1
            draw_blockers.append("draw:order-invalid")
        if draw_order != index:
            draw_blockers.append("draw:order-not-contiguous")

        resource = draw.get("resource") or {}
        if not isinstance(resource, Mapping):
            resource = {}
            draw_blockers.append("draw:resource-missing")
        path = _norm(resource.get("path"))
        archive = str(resource.get("archive") or "")
        digest = _sha(resource.get("sha256"))
        if not path:
            draw_blockers.append("draw:resource-path-missing")
        if archive.lower() != selected_archive_name.lower():
            draw_blockers.append("draw:resource-archive-mismatch")
        if digest is None:
            draw_blockers.append("draw:resource-sha256-invalid")

        hits = [
            row for row in resources
            if str(row.get("archive_id") or "") == selected_archive_id
            and _norm(row.get("path")) == path
        ]
        if len(hits) != 1:
            draw_blockers.append(
                "draw:catalog-resource-" + ("missing" if not hits else f"ambiguous:{len(hits)}")
            )
            catalog_row = None
        else:
            catalog_row = hits[0]
            catalog_sha = _sha(catalog_row.get("decoded_sha256"))
            if catalog_sha is None:
                draw_blockers.append("draw:catalog-resource-not-decoded")
            elif digest is not None and catalog_sha != digest:
                draw_blockers.append("draw:catalog-resource-sha256-mismatch")
            if str(catalog_row.get("extension") or "").lower() != ".imb":
                draw_blockers.append("draw:catalog-resource-not-imb")

        joined.append({
            "draw_order": draw_order,
            "binding_index": draw.get("binding_index"),
            "scene_draw_identity_sha256": draw.get("scene_draw_identity_sha256"),
            "resource": dict(resource),
            "catalog_resource_id": catalog_row.get("id") if catalog_row is not None else None,
            "ready": not draw_blockers,
            "blocking_reasons": list(dict.fromkeys(draw_blockers)),
        })
        blockers.extend(f"draw-{index}:{reason}" for reason in draw_blockers)

    if scene_set and not draws:
        blockers.append("scene-set:draws-missing")

    blockers = list(dict.fromkeys(blockers))
    ready = bool(joined) and all(row["ready"] for row in joined) and not blockers
    return {
        "format": SCENE_JOIN_FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "track": bootstrap.get("track"),
        "source_archive": selected_archive_name or None,
        "draw_count": len(joined),
        "draws": joined,
        "source": {
            "scene_set_format": scene_set.get("format") if isinstance(scene_set, Mapping) else None,
            "scene_prepare_format": scene_prepare.get("format") if isinstance(scene_prepare, Mapping) else None,
        },
        "boundary": {
            "runtime_scene_evidence_required": True,
            "scene_set_generated_from_static_resources": False,
            "exact_imb_archive_path_sha256_join": True,
            "scene_coverage_invented": False,
            "shader_permutation_invented": False,
        },
    }


def build_native_resource_handoff(
    catalog: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    physics_bundle: Mapping[str, Any],
    *,
    scene_set: Mapping[str, Any] | None = None,
    scene_prepare: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    physics_manifest = build_vehicle_physics_resource_manifest(
        catalog, bootstrap, physics_bundle
    )
    bmw_compat = build_bmw_m3_runtime_compat_manifest(physics_manifest)
    scene_join = build_scene_catalog_join(
        catalog, bootstrap, scene_set, scene_prepare
    )

    blockers: list[str] = []
    if bmw_compat.get("ready") is not True:
        blockers.extend(
            "physics:" + str(reason)
            for reason in bmw_compat.get("blocking_reasons") or ["not-ready"]
        )
    if scene_join.get("ready") is not True:
        blockers.extend(
            "scene:" + str(reason)
            for reason in scene_join.get("blocking_reasons") or ["not-ready"]
        )
    blockers = list(dict.fromkeys(blockers))
    resource_inputs_ready = not blockers
    return {
        "format": HANDOFF_FORMAT,
        "version": 1,
        "status": "ready" if resource_inputs_ready else "blocked",
        "ready": resource_inputs_ready,
        "resource_inputs_ready": resource_inputs_ready,
        "blocking_reasons": blockers,
        "vehicle_physics_manifest": physics_manifest,
        "native_physics_compatibility": bmw_compat,
        "scene_catalog_join": scene_join,
        "boundary": {
            "native_resource_inputs_joined": resource_inputs_ready,
            "camera_state_evaluated": False,
            "participant_runtime_identity_evaluated": False,
            "body_feedback_packets_evaluated": False,
            "runtime_execution_claimed": False,
            "provenance_gate_bypass": False,
            "runtime_evidence_substitution": False,
            "missing_resource_synthesis": False,
        },
    }


def build_native_resource_handoff_files(
    catalog_path: str | Path,
    bootstrap_path: str | Path,
    physics_bundle_path: str | Path,
    output_dir: str | Path,
    *,
    scene_set_dir: str | Path | None = None,
) -> dict[str, Any]:
    catalog = _load(catalog_path)
    bootstrap = _load(bootstrap_path)
    physics_bundle = _load(physics_bundle_path)

    scene_set = None
    scene_prepare = None
    file_blockers: list[str] = []
    scene_manifest_path: Path | None = None
    if scene_set_dir is not None:
        root = Path(scene_set_dir)
        scene_manifest_path = root / "bundle_set_manifest.json"
        prepare_path = root / "bundle_set_prepare.json"
        try:
            scene_set = _load(scene_manifest_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            file_blockers.append("scene-set-file:" + type(exc).__name__)
        try:
            scene_prepare = _load(prepare_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            file_blockers.append("scene-prepare-file:" + type(exc).__name__)

        if scene_set is not None and scene_prepare is not None:
            expected_sha = _sha((scene_prepare.get("source") or {}).get("manifest_sha256"))
            actual_sha = _file_sha256(scene_manifest_path)
            if expected_sha is None:
                file_blockers.append("scene-prepare:source-manifest-sha256-missing")
            elif expected_sha != actual_sha:
                file_blockers.append("scene-prepare:source-manifest-sha256-mismatch")

    handoff = build_native_resource_handoff(
        catalog,
        bootstrap,
        physics_bundle,
        scene_set=scene_set,
        scene_prepare=scene_prepare,
    )
    if file_blockers:
        handoff = dict(handoff)
        handoff["blocking_reasons"] = list(dict.fromkeys(
            list(handoff.get("blocking_reasons") or []) + file_blockers
        ))
        handoff["ready"] = False
        handoff["resource_inputs_ready"] = False
        handoff["status"] = "blocked"
        handoff["boundary"] = dict(handoff.get("boundary") or {})
        handoff["boundary"]["native_resource_inputs_joined"] = False

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    physics_manifest = handoff["vehicle_physics_manifest"]
    compatibility = handoff["native_physics_compatibility"]
    scene_join = handoff["scene_catalog_join"]

    paths = {
        "vehicle_physics_manifest": out / "vehicle_physics_resource_manifest.json",
        "scene_catalog_join": out / "scene_catalog_join.json",
        "handoff": out / "native_resource_handoff.json",
    }
    if compatibility.get("ready") is True:
        paths["native_physics_manifest"] = out / "native_physics_manifest.json"

    for key, value in (
        ("vehicle_physics_manifest", physics_manifest),
        ("scene_catalog_join", scene_join),
    ):
        path = paths[key]
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if "native_physics_manifest" in paths:
        paths["native_physics_manifest"].write_text(
            json.dumps(compatibility, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    handoff = dict(handoff)
    handoff["artifacts"] = {
        key: {
            "path": str(path),
            "sha256": _file_sha256(path),
        }
        for key, path in paths.items()
        if key != "handoff" and path.is_file()
    }
    paths["handoff"].write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return handoff
