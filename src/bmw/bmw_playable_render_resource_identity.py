"""Fail-closed exact resource admission for the playable BMW body renderer.

Phase 533 builds renderer-ready material slices from the selected retail BMW,
cockpit and RENDER archives.  Some legacy helpers predate the current Process 3
identity policy and may tolerate a byte-identical duplicate or a shader basename
fallback.  This gate does not infer dependencies again.  Instead it revalidates
the exact resources that Phase 533 actually selected before the playable scene
may consume them.

FXO cache copies are intentionally outside this resource-occurrence gate.  Their
selected program is already carried by exact shader/permutation byte identities;
byte-identical cache copies may therefore remain a byte-equivalence class, but
this module never promotes one cache occurrence to semantic resource identity.
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
    if index is None or index < 0:
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
        return None, blockers
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
    blockers: list[str] = []
    claims: list[dict[str, Any]] = []
    provenance = material_slice.get("provenance")
    if not isinstance(provenance, Mapping):
        return [], [f"phase654:primitive-{primitive_index}:provenance-missing"]

    packet = material_slice.get("packet")
    packet_mesh = packet.get("mesh") if isinstance(packet, Mapping) else None
    mesh_ref = packet_mesh.get("ref") if isinstance(packet_mesh, Mapping) else None
    mesh, reasons = _claim(
        kind="mesh",
        primitive_index=primitive_index,
        raw=provenance.get("mesh_entry") if isinstance(provenance, Mapping) else None,
        expected_logical_path=mesh_ref,
    )
    blockers.extend(reasons)
    if mesh is not None:
        claims.append(mesh)

    material, reasons = _claim(
        kind="material",
        primitive_index=primitive_index,
        raw=provenance.get("material_entry") if isinstance(provenance, Mapping) else None,
        expected_logical_path=material_slice.get("material_bmt"),
    )
    blockers.extend(reasons)
    if material is not None:
        claims.append(material)

    binding = material_slice.get("material_binding")
    shader_ref = binding.get("shader") if isinstance(binding, Mapping) else None
    shader_source = provenance.get("shader_source")
    if not isinstance(shader_source, Mapping):
        blockers.append(f"phase654:primitive-{primitive_index}:shader:provenance-missing")
    elif shader_source.get("kind") != "bff-entry":
        # The playable resource-driven path must be rooted in the already
        # admitted retail archives.  A caller-supplied external file has no
        # archive-local resource identity in this contract.
        blockers.append(
            f"phase654:primitive-{primitive_index}:shader:external-source-not-admissible"
        )
    else:
        shader, reasons = _claim(
            kind="shader",
            primitive_index=primitive_index,
            raw=shader_source,
            expected_logical_path=shader_ref,
        )
        blockers.extend(reasons)
        if shader is not None:
            claims.append(shader)

    raw_dds = provenance.get("dds_sources")
    if raw_dds is None:
        raw_dds = []
    if not isinstance(raw_dds, list):
        blockers.append(f"phase654:primitive-{primitive_index}:dds-sources-not-list")
        raw_dds = []
    for source_index, raw in enumerate(raw_dds):
        dds, reasons = _claim(
            kind=f"texture-{source_index}",
            primitive_index=primitive_index,
            raw=raw if isinstance(raw, Mapping) else None,
        )
        blockers.extend(reasons)
        if dds is not None:
            claims.append(dds)

    return claims, blockers


def build_bmw_playable_render_resource_identity_gate(
    admission: Mapping[str, Any],
    archive_paths: Mapping[str, str | Path],
) -> dict[str, Any]:
    blockers: list[str] = []
    if admission.get("format") != ADMISSION_FORMAT:
        blockers.append("phase654:body-material-admission-format-invalid")
    if admission.get("ready") is not True:
        blockers.append("phase654:body-material-admission-not-ready")

    required_roles = ("primary", "cockpit", "render")
    paths: dict[str, Path] = {}
    archive_identity: dict[str, dict[str, Any]] = {}
    for role in required_roles:
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

    # Multiple body primitives may depend on the same exact resource.  Merge
    # identical claims by logical path, but never merge different archive/index
    # provenance merely because payload hashes happen to be equal.
    claims_by_path: dict[str, dict[str, Any]] = {}
    for claim in raw_claims:
        key = str(claim["normalized_path"])
        existing = claims_by_path.get(key)
        if existing is None:
            claims_by_path[key] = dict(claim)
            continue
        identity = (claim["archive"], claim["index"], claim["sha256"])
        existing_identity = (
            existing["archive"],
            existing["index"],
            existing["sha256"],
        )
        if identity != existing_identity:
            blockers.append(f"phase654:claim-conflict:{key}")
            continue
        existing["primitive_indices"] = sorted(set(
            [*existing.get("primitive_indices", []), *claim.get("primitive_indices", [])]
        ))

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
            if int(entry.index) != int(claim["index"]):
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
            "payload_sha256_revalidated": True,
            "fxo_cache_byte_equivalence_is_resource_identity": False,
            "fxo_cache_semantic_source_selected_here": False,
            "external_shader_source_allowed": False,
            "runtime_instance_identity_claimed": False,
        },
    }
