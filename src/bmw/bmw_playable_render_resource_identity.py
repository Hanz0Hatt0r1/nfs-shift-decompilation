"""Fail-closed exact resource admission for the playable BMW body renderer.

The legacy Phase 533 BMW material helpers may accept byte-identical duplicate
resources or a shader basename fallback.  The playable path must not.  This
module revalidates the MEB/BMT/FX/DDS resources actually selected by Phase 533
against the already admitted BMW, cockpit and RENDER archives before Phase 644
may consume the material slice.

FXO cache copies are intentionally not resource-selected here.  The renderer
uses their exact program/permutation byte identities; repeated cache copies may
remain a byte-equivalence class, but this gate never promotes one occurrence to
semantic resource identity.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from shift_importer import BFF

FORMAT = "SHIFT.BMWPlayableRenderResourceIdentityGate/1"
ADMISSION_FORMAT = "SHIFT.BMWBodyMaterialAdmission/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").casefold()


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _claim(
    *,
    kind: str,
    primitive_index: int,
    raw: Mapping[str, Any] | None,
    expected_logical_path: Any = None,
    require_index: bool = True,
) -> tuple[dict[str, Any] | None, list[str]]:
    prefix = f"phase654:primitive-{primitive_index}:{kind}"
    if not isinstance(raw, Mapping):
        return None, [prefix + ":provenance-missing"]

    path = str(raw.get("path") or "")
    archive = str(raw.get("archive") or "")
    index = _safe_int(raw.get("index"))
    sha256 = str(raw.get("sha256") or "").casefold()
    blockers: list[str] = []
    if not _norm(path):
        blockers.append(prefix + ":path-missing")
    if not archive:
        blockers.append(prefix + ":archive-missing")
    if require_index and (index is None or index < 0):
        blockers.append(prefix + ":entry-index-invalid")
    if index is not None and index < 0:
        blockers.append(prefix + ":entry-index-invalid")
    if len(sha256) != 64:
        blockers.append(prefix + ":sha256-invalid")

    expected = _norm(expected_logical_path)
    if expected and _norm(path) != expected:
        blockers.append(
            prefix
            + ":logical-path-mismatch:expected="
            + expected
            + ":observed="
            + _norm(path)
        )
    if blockers:
        return None, list(dict.fromkeys(blockers))
    return {
        "kind": kind,
        "path": path,
        "normalized_path": _norm(path),
        "archive": archive,
        "index": index,
        "sha256": sha256,
        "primitive_indices": [primitive_index],
    }, []


def _slice_claims(
    primitive_index: int,
    material_slice: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    provenance = material_slice.get("provenance")
    if not isinstance(provenance, Mapping):
        return [], [f"phase654:primitive-{primitive_index}:provenance-missing"]

    blockers: list[str] = []
    claims: list[dict[str, Any]] = []
    packet = material_slice.get("packet")
    packet_mesh = packet.get("mesh") if isinstance(packet, Mapping) else None
    mesh_ref = packet_mesh.get("ref") if isinstance(packet_mesh, Mapping) else None

    for kind, raw, expected in (
        ("mesh", provenance.get("mesh_entry"), mesh_ref),
        ("material", provenance.get("material_entry"), material_slice.get("material_bmt")),
    ):
        claim, reasons = _claim(
            kind=kind,
            primitive_index=primitive_index,
            raw=raw if isinstance(raw, Mapping) else None,
            expected_logical_path=expected,
        )
        blockers.extend(reasons)
        if claim is not None:
            claims.append(claim)

    binding = material_slice.get("material_binding")
    shader_ref = binding.get("shader") if isinstance(binding, Mapping) else None
    shader_source = provenance.get("shader_source")
    if not isinstance(shader_source, Mapping):
        blockers.append(f"phase654:primitive-{primitive_index}:shader:provenance-missing")
    elif shader_source.get("kind") != "bff-entry":
        blockers.append(
            f"phase654:primitive-{primitive_index}:shader:external-source-not-admissible"
        )
    else:
        claim, reasons = _claim(
            kind="shader",
            primitive_index=primitive_index,
            raw=shader_source,
            expected_logical_path=shader_ref,
        )
        blockers.extend(reasons)
        if claim is not None:
            claims.append(claim)

    raw_dds = provenance.get("dds_sources")
    if raw_dds is None:
        raw_dds = []
    if not isinstance(raw_dds, list):
        blockers.append(f"phase654:primitive-{primitive_index}:dds-sources-not-list")
        raw_dds = []
    for source_index, raw in enumerate(raw_dds):
        claim, reasons = _claim(
            kind=f"texture-{source_index}",
            primitive_index=primitive_index,
            raw=raw if isinstance(raw, Mapping) else None,
            # Legacy DDS provenance did not retain entry index.  The unique
            # exact occurrence found below becomes the authoritative index.
            require_index=False,
        )
        blockers.extend(reasons)
        if claim is not None:
            claims.append(claim)
    return claims, blockers


def _merge_claims(raw_claims: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    by_path: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for claim in raw_claims:
        key = str(claim["normalized_path"])
        existing = by_path.get(key)
        if existing is None:
            by_path[key] = dict(claim)
            continue
        # A missing legacy DDS index may merge with the exact index from another
        # primitive claim; any two concrete and different indices remain a
        # provenance conflict.
        existing_index = existing.get("index")
        claim_index = claim.get("index")
        index_conflict = (
            existing_index is not None
            and claim_index is not None
            and existing_index != claim_index
        )
        if (
            existing["archive"] != claim["archive"]
            or existing["sha256"] != claim["sha256"]
            or index_conflict
        ):
            blockers.append(f"phase654:claim-conflict:{key}")
            continue
        if existing_index is None and claim_index is not None:
            existing["index"] = claim_index
        existing["primitive_indices"] = sorted(set(
            [*existing.get("primitive_indices", []), *claim.get("primitive_indices", [])]
        ))
    return by_path, blockers


def build_bmw_playable_render_resource_identity_gate(
    admission: Mapping[str, Any],
    archive_paths: Mapping[str, str | Path],
) -> dict[str, Any]:
    blockers: list[str] = []
    if admission.get("format") != ADMISSION_FORMAT:
        blockers.append("phase654:body-material-admission-format-invalid")
    if admission.get("ready") is not True:
        blockers.append("phase654:body-material-admission-not-ready")

    paths: dict[str, Path] = {}
    archive_identity: dict[str, dict[str, Any]] = {}
    for role in ("primary", "cockpit", "render"):
        raw = archive_paths.get(role)
        if raw is None:
            blockers.append(f"phase654:archive-role-missing:{role}")
            continue
        path = Path(raw)
        if not path.is_file():
            blockers.append(f"phase654:archive-file-missing:{role}:{path}")
            continue
        paths[role] = path
        archive_identity[role] = {
            "name": path.name,
            "sha256": _sha256_file(path),
            "size": path.stat().st_size,
        }

    raw_claims: list[dict[str, Any]] = []
    primitive_results = admission.get("primitive_results")
    if not isinstance(primitive_results, list) or not primitive_results:
        blockers.append("phase654:primitive-results-missing")
        primitive_results = []
    for raw_row in primitive_results:
        if not isinstance(raw_row, Mapping):
            blockers.append("phase654:primitive-result-not-object")
            continue
        primitive_index = _safe_int(raw_row.get("primitive_index"))
        if primitive_index is None or primitive_index < 0:
            blockers.append("phase654:primitive-index-invalid")
            continue
        if raw_row.get("ready") is not True:
            blockers.append(f"phase654:primitive-{primitive_index}:not-ready")
            continue
        material_slice = raw_row.get("slice")
        if not isinstance(material_slice, Mapping):
            blockers.append(f"phase654:primitive-{primitive_index}:slice-missing")
            continue
        claims, reasons = _slice_claims(primitive_index, material_slice)
        raw_claims.extend(claims)
        blockers.extend(reasons)

    claims_by_path, merge_blockers = _merge_claims(raw_claims)
    blockers.extend(merge_blockers)
    verified: list[dict[str, Any]] = []
    archives: list[tuple[str, BFF]] = []
    try:
        for role, path in paths.items():
            archives.append((role, BFF(path)))
        occurrence_index: dict[str, list[tuple[str, BFF, Any]]] = {}
        for role, archive in archives:
            for entry in archive.entries:
                occurrence_index.setdefault(_norm(entry.path), []).append(
                    (role, archive, entry)
                )

        for key, claim in sorted(claims_by_path.items()):
            hits = occurrence_index.get(key, [])
            if len(hits) != 1:
                detail = ",".join(
                    f"{role}:{archive.path.name}:{entry.index}"
                    for role, archive, entry in hits
                ) or "none"
                blockers.append(
                    f"phase654:exact-resource-occurrence-count:{key}:"
                    f"expected=1:observed={len(hits)}:{detail}"
                )
                continue

            role, archive, entry = hits[0]
            payload = archive.extract_entry(entry)
            digest = _sha256_bytes(payload)
            row_blockers: list[str] = []
            if archive.path.name.casefold() != str(claim["archive"]).casefold():
                row_blockers.append("archive-mismatch")
            claimed_index = claim.get("index")
            if claimed_index is not None and int(entry.index) != int(claimed_index):
                row_blockers.append("entry-index-mismatch")
            if digest != claim["sha256"]:
                row_blockers.append("payload-sha256-mismatch")
            if row_blockers:
                blockers.extend(
                    f"phase654:resource-claim-mismatch:{key}:{reason}"
                    for reason in row_blockers
                )
                continue
            verified.append({
                **claim,
                "archive_role": role,
                "observed_archive": archive.path.name,
                "observed_index": int(entry.index),
                "observed_sha256": digest,
                "size": len(payload),
                "ready": True,
            })
    except Exception as exc:
        blockers.append(
            "phase654:archive-resource-validation-failed:"
            f"{type(exc).__name__}:{exc}"
        )
    finally:
        for _role, archive in archives:
            archive.close()

    blockers = list(dict.fromkeys(blockers))
    ready = (
        not blockers
        and bool(claims_by_path)
        and len(verified) == len(claims_by_path)
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "archive_identity": archive_identity,
        "summary": {
            "primitive_count": sum(
                1
                for row in primitive_results
                if isinstance(row, Mapping) and row.get("ready") is True
            ),
            "claimed_resource_count": len(claims_by_path),
            "verified_resource_count": len(verified),
        },
        "resources": verified,
        "boundary": {
            "caller_exact_archive_admission_required": True,
            "exact_logical_path_required": True,
            "exact_single_occurrence_required": True,
            "basename_fallback_allowed": False,
            "archive_order_is_selection_authority": False,
            "first_duplicate_selection_allowed": False,
            "byte_identical_duplicate_is_semantic_identity": False,
            "legacy_dds_index_may_be_derived_only_from_unique_exact_occurrence": True,
            "payload_sha256_revalidated": True,
            "fxo_cache_byte_equivalence_is_resource_identity": False,
            "fxo_cache_semantic_source_selected_here": False,
            "external_shader_source_allowed": False,
            "runtime_instance_identity_claimed": False,
        },
    }
