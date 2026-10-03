"""Fail-closed offline SHIFT BFF catalog, dependency graph and bootstrap orchestration."""
from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from collections import Counter, defaultdict
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Sequence

from shift_importer import BFF, classify
from resource_formats import analyze_decoded_resource, parse_bmt_material, parse_vhf_scene
from meb_format import read_meb
from imb_neutral_geometry import build_imb_neutral_geometry
from imx_neutral_geometry import build_imx_neutral_geometry

CATALOG_FORMAT = "SHIFT.OfflineResourceCatalog/1"
GRAPH_FORMAT = "SHIFT.OfflineResourceDependencyGraph/1"
COVERAGE_FORMAT = "SHIFT.OfflineResourceCoverage/1"
BOOTSTRAP_FORMAT = "SHIFT.SceneVehicleBootstrap/1"
ADMISSION_FORMAT = "SHIFT.OfflineResourceRuntimeAdmission/1"

KNOWN_DECODE_EXTENSIONS = {
    ".bmt", ".meb", ".vhf", ".imb", ".imx", ".csm", ".bml", ".sgb",
    ".dds", ".xml", ".fx", ".fxh", ".bab", ".bas", ".lod",
}
VEHICLE_PHYSICS_EXTENSIONS = (".cdf", ".edf", ".gdf", ".sdf", ".tbf", ".bbf")
TRACK_VISUAL_ROOT_EXTENSIONS = (".sgb", ".trd", ".lsd")
TRACK_PHYSICS_ROOT_EXTENSIONS = (".aiw", ".csm")
VEHICLE_RENDER_ROOT_EXTENSIONS = (".vhf",)


@dataclass(frozen=True)
class MaterializedArchive:
    source: str
    member: str | None
    path: Path

    @property
    def display_name(self) -> str:
        return self.member or self.path.name


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _safe_member(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"unsafe ZIP member/resource path: {value!r}")
    return path


@contextmanager
def materialize_bff_inputs(inputs: Iterable[str | Path]) -> Iterator[list[MaterializedArchive]]:
    rows: list[MaterializedArchive] = []
    with ExitStack() as stack:
        for input_index, raw in enumerate(inputs):
            source = Path(raw)
            if source.is_dir():
                rows.extend(
                    MaterializedArchive(str(source), None, path)
                    for path in sorted(source.rglob("*.bff"))
                )
                continue
            if source.suffix.lower() == ".bff":
                if not source.is_file():
                    raise FileNotFoundError(source)
                rows.append(MaterializedArchive(str(source), None, source))
                continue
            if source.suffix.lower() != ".zip":
                raise ValueError(f"expected .bff, .zip, or directory: {source}")
            if not source.is_file():
                raise FileNotFoundError(source)
            archive = zipfile.ZipFile(source)
            stack.callback(archive.close)
            root = Path(stack.enter_context(
                tempfile.TemporaryDirectory(prefix=f"shift-offline-{input_index:02d}-")
            ))
            for name in sorted(archive.namelist()):
                if not name.lower().endswith(".bff") or name.endswith("/"):
                    continue
                member = _safe_member(name)
                target = root.joinpath(*member.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
                rows.append(MaterializedArchive(str(source), name, target))
        yield rows


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _source_kind(materialized: MaterializedArchive) -> str:
    if materialized.member is not None:
        return "zip-member"
    source = Path(materialized.source)
    if source.suffix.lower() == ".bff":
        return "bff"
    return "directory-bff"


def _duplicate_identity_groups(
    resources: Sequence[dict[str, Any]],
    *,
    field: str,
    identity_kind: str,
) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in resources:
        value = row.get(field)
        if value in (None, ""):
            continue
        buckets[str(value)].append(row)

    groups: list[dict[str, Any]] = []
    for value, rows in buckets.items():
        if len(rows) < 2:
            continue
        groups.append({
            "identity_kind": identity_kind,
            "identity": value,
            "occurrences": len(rows),
            "resource_ids": sorted(str(row["id"]) for row in rows),
            "archive_ids": sorted({str(row["archive_id"]) for row in rows}),
            "paths": sorted({str(row["path"]) for row in rows}),
        })
    groups.sort(key=lambda row: (-int(row["occurrences"]), str(row["identity"])))
    return groups


def _archive_id(materialized: MaterializedArchive, index: int) -> str:
    token = f"{materialized.source}\n{materialized.member or materialized.path.name}"
    return f"bff-{index:04d}-" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def _material_ref(value: Any) -> str | None:
    ref = str(value or "").replace("\\", "/")
    if ref.lower().endswith(".mtx"):
        return ref[:-4] + ".bmt"
    return ref if ref.lower().endswith(".bmt") else None


def _vhf_refs(scene: dict[str, Any]) -> list[str]:
    refs: list[str] = []

    def walk(node: dict[str, Any]) -> None:
        for ref in node.get("resources") or []:
            value = str(ref).replace("\\", "/")
            if value and value not in refs:
                refs.append(value)
        for child in node.get("children") or []:
            walk(child)

    for node in scene.get("nodes") or []:
        walk(node)
    return refs


def _semantic_dependencies(
    path: str,
    payload: bytes,
    analysis: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    ext = Path(path.replace("\\", "/")).suffix.lower()
    dependencies: list[dict[str, Any]] = []
    neutral: dict[str, Any] | None = None

    def add(ref: Any, kind: str, scope: str, parser: str) -> None:
        value = str(ref or "").replace("\\", "/").strip()
        if not value:
            return
        dependencies.append({
            "ref": value,
            "kind": kind,
            "scope": scope,
            "parser": parser,
            "evidence": "semantic-parser",
            "admissible": True,
        })

    if ext == ".bmt":
        parsed = parse_bmt_material(payload)
        material = parsed.get("material") or {}
        add(material.get("shader"), "shader-source", "global-exact", "parse_bmt_material")
        for texture in material.get("textures") or []:
            add(texture, "texture", "same-archive-exact", "parse_bmt_material")
        neutral = {
            "format": parsed.get("format"),
            "material": material.get("name"),
            "technique": material.get("technique"),
            "shader": material.get("shader"),
            "texture_count": len(material.get("textures") or []),
        }
    elif ext == ".meb":
        mesh = read_meb(payload)
        for primitive in mesh.primitives:
            ref = _material_ref(primitive.material)
            if ref:
                add(ref, "material", "same-archive-exact", "meb_format.read_meb")
        neutral = {
            "format": "SHIFT.MEBNeutralSummary/1",
            "vertex_count": len(getattr(mesh, "vertices", []) or []),
            "primitive_count": len(mesh.primitives),
            "material_reference_count": len({d["ref"].lower() for d in dependencies}),
        }
    elif ext in {".imb", ".imx"}:
        parser_name = (
            "build_imb_neutral_geometry" if ext == ".imb"
            else "build_imx_neutral_geometry"
        )
        parsed = (
            build_imb_neutral_geometry(payload) if ext == ".imb"
            else build_imx_neutral_geometry(payload)
        )
        for primitive in parsed.get("primitives") or []:
            ref = _material_ref(primitive.get("material"))
            if ref:
                add(ref, "material", "same-archive-exact", parser_name)
        neutral = {
            "format": parsed.get("format"),
            "status": parsed.get("status"),
            "ready": parsed.get("ready"),
            "primitive_count": parsed.get("primitive_count"),
            "decoded_properties": parsed.get("decoded_properties"),
            "deferred_stream_count": parsed.get("deferred_stream_count"),
            "blocking_reasons": parsed.get("blocking_reasons") or [],
        }
    elif ext == ".vhf":
        scene = parse_vhf_scene(payload)
        for ref in _vhf_refs(scene):
            add(ref, "geometry", "same-archive-exact", "parse_vhf_scene")
        neutral = {
            "format": scene.get("format"),
            "name": scene.get("name"),
            "stats": scene.get("stats"),
            "resource_reference_count": len(dependencies),
        }
    elif ext == ".sgb":
        parsed = (analysis.get("analysis") or {})
        # Current SGB resource_refs are produced by a string scan. Preserve them
        # for diagnostics, but never use them to close an admission dependency.
        for ref in parsed.get("resource_refs") or []:
            value = str(ref.get("path") or "").replace("\\", "/").strip()
            if value:
                dependencies.append({
                    "ref": value,
                    "kind": str(ref.get("kind") or "resource"),
                    "scope": "diagnostic-only",
                    "parser": "resource_formats.parse_sgb",
                    "evidence": str(ref.get("confidence") or "string-scan"),
                    "admissible": False,
                })
        neutral = {
            "format": parsed.get("format"),
            "chunk_count": parsed.get("chunk_count"),
            "resource_ref_counts": parsed.get("resource_ref_counts"),
            "trailing_bytes": parsed.get("trailing_bytes"),
        }
    else:
        parsed = analysis.get("analysis") or {}
        neutral = {
            "format": parsed.get("format"),
            "analysis_error": analysis.get("analysis_error"),
        }
    return dependencies, neutral


def _resolve_ref(
    ref: str,
    scope: str,
    source_archive_id: str,
    global_index: dict[str, list[str]],
    archive_index: dict[str, dict[str, list[str]]],
) -> list[str]:
    key = _norm(ref)
    candidates = [key]
    if key.endswith(".mtx"):
        candidates.append(key[:-4] + ".bmt")
    elif key.endswith(".bmt"):
        candidates.append(key[:-4] + ".mtx")
    hits: list[str] = []
    seen: set[str] = set()
    index = archive_index.get(source_archive_id, {}) if scope == "same-archive-exact" else global_index
    for candidate in candidates:
        for resource_id in index.get(candidate, []):
            if resource_id not in seen:
                seen.add(resource_id)
                hits.append(resource_id)
    return hits


def _validation_summary(
    resources: Sequence[dict[str, Any]],
    blocking_edges: Sequence[dict[str, Any]],
) -> dict[str, int]:
    supported = [row for row in resources if row.get("extension") in KNOWN_DECODE_EXTENSIONS]
    blocked = [row for row in resources if row.get("decode_status") == "blocked"]
    # Parsers currently expose generic exceptions/analysis_error for failures.
    # Do not infer malformed or unknown-version/layout from exception text.
    malformed = [row for row in blocked if row.get("validation_failure_kind") == "malformed"]
    unknown_layout = [
        row for row in blocked
        if row.get("validation_failure_kind") == "unknown-version-or-layout"
    ]
    explicitly_classified = {str(row.get("id")) for row in malformed + unknown_layout}
    unresolved_sources = {
        str(edge.get("source_id")) for edge in blocking_edges if edge.get("source_id")
    }
    return {
        "total": len(resources),
        "supported": len(supported),
        "verified": sum(1 for row in resources if row.get("decode_status") == "parsed"),
        "blocked": len(blocked),
        "unsupported": sum(1 for row in resources if row.get("decode_status") == "unsupported"),
        "deferred": sum(1 for row in resources if row.get("decode_status") == "deferred"),
        "malformed": len(malformed),
        "unknown_version_layout": len(unknown_layout),
        "unclassified_blocked": sum(
            1 for row in blocked if str(row.get("id")) not in explicitly_classified
        ),
        "unresolved_dependency_edges": len(blocking_edges),
        "unresolved_dependency_resources": len(unresolved_sources),
    }


def build_catalog(
    materialized: Sequence[MaterializedArchive],
    *,
    decode_known: bool = False,
    decode_limit_per_archive: int = 0,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if decode_limit_per_archive < 0:
        raise ValueError("decode_limit_per_archive must be non-negative")
    archives: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    pending_dependencies: list[dict[str, Any]] = []
    extension_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    compression_counts: Counter[str] = Counter()
    decode_counts: Counter[str] = Counter()
    parser_failures: list[dict[str, Any]] = []

    for archive_index_value, materialized_archive in enumerate(materialized):
        archive_id = _archive_id(materialized_archive, archive_index_value)
        archive_sha256 = _sha256_file(materialized_archive.path)
        with BFF(materialized_archive.path) as archive:
            encryption = "rc4" if int(archive.x12d) == 2 else "none"
            archive_row = {
                "id": archive_id,
                "source": materialized_archive.source,
                "source_member": materialized_archive.member,
                "source_kind": _source_kind(materialized_archive),
                "archive_name": materialized_archive.display_name.split("/")[-1],
                "bytes": materialized_archive.path.stat().st_size,
                "sha256": archive_sha256,
                "version": int(archive.version),
                "x12d": int(archive.x12d),
                "encryption": encryption,
                "entry_count": len(archive.entries),
            }
            archives.append(archive_row)
            decoded_here = 0
            for entry in archive.entries:
                path = entry.path.replace("\\", "/")
                ext = Path(path).suffix.lower()
                extension_counts[ext or "<none>"] += 1
                compression_counts[str(int(entry.type))] += 1
                resource_id = f"{archive_id}#{int(entry.index)}"
                raw = archive.raw_payload(entry)
                row: dict[str, Any] = {
                    "id": resource_id,
                    "archive_id": archive_id,
                    "archive_name": archive_row["archive_name"],
                    "index": int(entry.index),
                    "path": path,
                    "normalized_path": _norm(path),
                    "extension": ext,
                    "category": classify(path),
                    "offset": int(entry.offset),
                    "compression_type": int(entry.type),
                    "compressed_size": int(entry.compressed_size),
                    "uncompressed_size": int(entry.uncompressed_size),
                    "crc32_field": int(entry.crc32_field),
                    "fileext": int(entry.fileext),
                    "encryption": encryption,
                    "raw_sha256": _sha256(raw),
                    "decode_status": "deferred" if ext in KNOWN_DECODE_EXTENSIONS else "unsupported",
                    "dependencies": [],
                }
                category_counts[row["category"]] += 1
                should_decode = (
                    decode_known
                    and ext in KNOWN_DECODE_EXTENSIONS
                    and (decode_limit_per_archive == 0 or decoded_here < decode_limit_per_archive)
                )
                if should_decode:
                    decoded_here += 1
                    try:
                        payload = archive.extract_entry(entry, type2="lzx")
                        analysis = analyze_decoded_resource(path, payload)
                        deps, neutral = _semantic_dependencies(path, payload, analysis)
                        analysis_error = analysis.get("analysis_error")
                        row.update({
                            "decoded_sha256": _sha256(payload),
                            "decoded_size": len(payload),
                            "analysis_format": (analysis.get("analysis") or {}).get("format"),
                            "analysis_error": analysis_error,
                            "neutral_ir": neutral,
                            "dependencies": deps,
                            "decode_status": "blocked" if analysis_error else "parsed",
                        })
                        pending_dependencies.extend(
                            {"source_id": resource_id, "source_archive_id": archive_id, "source_path": path, **dep}
                            for dep in deps
                        )
                        if analysis_error:
                            parser_failures.append({
                                "resource_id": resource_id,
                                "path": path,
                                "error": str(analysis_error),
                            })
                    except Exception as exc:
                        row.update({
                            "decode_status": "blocked",
                            "error_kind": type(exc).__name__,
                            "error": str(exc),
                        })
                        parser_failures.append({
                            "resource_id": resource_id,
                            "path": path,
                            "error_kind": type(exc).__name__,
                            "error": str(exc),
                        })
                decode_counts[row["decode_status"]] += 1
                resources.append(row)

    global_index: dict[str, list[str]] = defaultdict(list)
    archive_path_index: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in resources:
        global_index[row["normalized_path"]].append(row["id"])
        archive_path_index[row["archive_id"]][row["normalized_path"]].append(row["id"])

    path_duplicates = _duplicate_identity_groups(
        resources, field="normalized_path", identity_kind="normalized-path"
    )
    raw_duplicates = _duplicate_identity_groups(
        resources, field="raw_sha256", identity_kind="stored-payload-sha256"
    )
    decoded_duplicates = _duplicate_identity_groups(
        resources, field="decoded_sha256", identity_kind="decoded-payload-sha256"
    )

    edges: list[dict[str, Any]] = []
    for dep in pending_dependencies:
        if not dep["admissible"]:
            edges.append({**dep, "status": "diagnostic", "targets": []})
            continue
        hits = _resolve_ref(
            dep["ref"], dep["scope"], dep["source_archive_id"],
            global_index, archive_path_index,
        )
        edges.append({
            **dep,
            "targets": hits,
            "status": "resolved" if len(hits) == 1 else "missing" if not hits else "ambiguous",
        })

    blocking_edges = [e for e in edges if e["admissible"] and e["status"] != "resolved"]
    graph = {
        "format": GRAPH_FORMAT,
        "version": 1,
        "edges": edges,
        "summary": {
            "edges": len(edges),
            "admissible_edges": sum(1 for e in edges if e["admissible"]),
            "diagnostic_edges": sum(1 for e in edges if not e["admissible"]),
            "resolved_admissible_edges": sum(1 for e in edges if e["admissible"] and e["status"] == "resolved"),
            "blocking_admissible_edges": len(blocking_edges),
        },
        "boundary": {
            "authoritative_dependencies": "semantic-parser-only",
            "basename_fallback": False,
            "sgb_string_scan_closes_dependencies": False,
            "known_aliases": [".mtx<->.bmt"],
        },
    }
    catalog = {
        "format": CATALOG_FORMAT,
        "version": 1,
        "archives": archives,
        "resources": resources,
        "duplicate_identities": {
            "normalized_path": path_duplicates,
            "stored_payload_sha256": raw_duplicates,
            "decoded_payload_sha256": decoded_duplicates,
            "limitations": [
                "Normalized-path equality does not prove payload equality.",
                "Stored-payload SHA-256 equality proves exact BFF payload-byte equality only.",
                "Decoded-payload SHA-256 equality proves decoded-byte equality only for resources that were decoded.",
                "No material, shader-permutation, format-layout, or runtime semantic equivalence is inferred.",
            ],
        },
        "summary": {
            "archives": len(archives),
            "resources": len(resources),
            "extensions": dict(sorted(extension_counts.items())),
            "categories": dict(sorted(category_counts.items())),
            "compression_types": dict(sorted(compression_counts.items())),
            "decode_status": dict(sorted(decode_counts.items())),
            "duplicate_normalized_path_groups": len(path_duplicates),
            "duplicate_stored_payload_groups": len(raw_duplicates),
            "duplicate_decoded_payload_groups": len(decoded_duplicates),
        },
        "boundary": {
            "decode_known": bool(decode_known),
            "unknown_format_policy": "indexed-but-not-guessed",
            "runtime_evidence_substitution": False,
            "raw_sha256_semantics": "exact-stored-bff-payload-bytes",
            "duplicate_identity_semantics": "byte-or-path-identity-only-no-semantic-equivalence",
        },
    }
    coverage = {
        "format": COVERAGE_FORMAT,
        "version": 1,
        "archives": len(archives),
        "resources": len(resources),
        "parsed": int(decode_counts.get("parsed", 0)),
        "blocked": int(decode_counts.get("blocked", 0)),
        "unsupported": int(decode_counts.get("unsupported", 0)),
        "deferred": int(decode_counts.get("deferred", 0)),
        "validation": _validation_summary(resources, blocking_edges),
        "validation_boundary": {
            "supported_semantics": "extension-has-explicit-offline-decoder",
            "verified_semantics": "decoded-and-parser-completed-without-analysis_error",
            "malformed_requires_explicit_parser_classification": True,
            "unknown_version_layout_requires_explicit_parser_classification": True,
            "exception_text_classification": False,
            "generic_parser_failures": "unclassified_blocked",
        },
        "parser_failures": parser_failures,
        "unknown_extensions": sorted(
            ext for ext, count in extension_counts.items()
            if ext != "<none>" and all(
                row["category"] != "UNKNOWN" or row["extension"] != ext
                for row in resources
            ) is False
        ),
        "dependency_summary": graph["summary"],
        "ready": not parser_failures and not blocking_edges,
    }
    return catalog, graph, coverage


def write_catalog_bundle(
    output_dir: str | Path,
    catalog: dict[str, Any],
    graph: dict[str, Any],
    coverage: dict[str, Any],
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("resource_catalog.json", catalog),
        ("dependency_graph.json", graph),
        ("coverage_report.json", coverage),
    ):
        (out / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _archive(catalog, filename, blockers, label, optional=False):
    hits = [a for a in catalog["archives"] if a["archive_name"].lower() == filename.lower()]
    if len(hits) == 1:
        return hits[0]
    if not optional or hits:
        blockers.append(f"{label}-archive-" + ("missing" if not hits else f"ambiguous:{len(hits)}"))
    return None


def _unique_ext(resources, ext, blockers, label):
    hits = [r for r in resources if r["extension"] == ext]
    if len(hits) == 1:
        return hits[0]["id"]
    blockers.append(f"{label}{ext}-" + ("missing" if not hits else f"ambiguous:{len(hits)}"))
    return None


def build_bootstrap_manifest(catalog, graph, *, track: str, vehicle: str):
    blockers: list[str] = []
    selected: dict[str, Any] = {}
    candidates = {
        "track_visual": _archive(catalog, f"{track}.bff", blockers, "track-visual"),
        "track_physics": _archive(catalog, f"{track}_Physics.bff", blockers, "track-physics"),
        "vehicle": _archive(catalog, f"{vehicle}.bff", blockers, "vehicle"),
        "vehicle_cockpit": _archive(catalog, f"{vehicle}_Cockpit.bff", blockers, "vehicle-cockpit", True),
    }
    selected.update({k: v for k, v in candidates.items() if v is not None})
    roots: dict[str, Any] = {}
    for key, exts in (
        ("track_visual", TRACK_VISUAL_ROOT_EXTENSIONS),
        ("track_physics", TRACK_PHYSICS_ROOT_EXTENSIONS),
        ("vehicle", VEHICLE_PHYSICS_EXTENSIONS + VEHICLE_RENDER_ROOT_EXTENSIONS),
    ):
        meta = candidates.get(key)
        if meta is None:
            continue
        rows = [r for r in catalog["resources"] if r["archive_id"] == meta["id"]]
        labels = {
            "track_visual": "track-visual",
            "track_physics": "track-physics",
            "vehicle": "vehicle",
        }
        roots[key] = {
            ext: _unique_ext(rows, ext, blockers, labels[key])
            for ext in exts
        }
        if key == "track_visual":
            roots[key]["imb_resource_ids"] = [r["id"] for r in rows if r["extension"] == ".imb"]
            roots[key]["imx_resource_ids"] = [r["id"] for r in rows if r["extension"] == ".imx"]

    selected_ids = {r["id"] for r in selected.values()}
    edges = [e for e in graph["edges"] if e["source_archive_id"] in selected_ids]
    unresolved = [e for e in edges if e["admissible"] and e["status"] != "resolved"]
    blockers.extend(f"dependency-{e['status']}:{e['source_path']}->{e['ref']}" for e in unresolved)
    decoded_any = any(
        r.get("decode_status") in {"parsed", "blocked"}
        for r in catalog["resources"]
        if r["archive_id"] in selected_ids
    )
    if not decoded_any:
        blockers.append("dependency-validation-not-run:use --decode-known")
    ready = not blockers
    bootstrap = {
        "format": BOOTSTRAP_FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "track": track,
        "vehicle": vehicle,
        "selected_archives": selected,
        "roots": roots,
        "blocking_reasons": blockers,
        "unresolved_dependencies": unresolved,
        "boundary": {
            "archive_selection": "exact-filename",
            "required_root_selection": "unique-extension-within-selected-archive",
            "dependency_resolution": "admissible-semantic-edges-only",
            "heuristic_refs_close_gate": False,
        },
    }
    runtime_blockers = list(blockers)
    if ready:
        runtime_blockers.append("native-runtime-render/physics-handoffs-still-separate")
    admission = {
        "format": ADMISSION_FORMAT,
        "version": 1,
        "status": "resource-blocked" if not ready else "resource-ready-runtime-blocked",
        "resource_bootstrap_ready": ready,
        "native_runtime_ready": False,
        "blocking_reasons": runtime_blockers,
        "boundary": {
            "provenance_gate_bypass": False,
            "runtime_evidence_substitution": False,
            "missing_resource_synthesis": False,
            "static_shader_permutation_invention": False,
        },
    }
    return bootstrap, admission


def _root_ids(bootstrap: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for group in bootstrap.get("roots", {}).values():
        for value in group.values():
            if isinstance(value, str):
                out.append(value)
            elif isinstance(value, list):
                out.extend(str(item) for item in value)
    return list(dict.fromkeys(out))


def resource_closure_ids(bootstrap: dict[str, Any], graph: dict[str, Any]) -> list[str]:
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in graph.get("edges") or []:
        if edge.get("admissible") and edge.get("status") == "resolved" and len(edge.get("targets") or []) == 1:
            outgoing[str(edge["source_id"])].append(str(edge["targets"][0]))
    queue = list(_root_ids(bootstrap))
    seen: set[str] = set()
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        queue.extend(outgoing.get(current, []))
    return sorted(seen)


def extract_resource_closure(
    materialized: Sequence[MaterializedArchive],
    catalog: dict[str, Any],
    graph: dict[str, Any],
    bootstrap: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Any]:
    wanted = set(resource_closure_ids(bootstrap, graph))
    by_archive = {row["id"]: row for row in catalog["archives"]}
    by_resource = {row["id"]: row for row in catalog["resources"]}
    materialized_by_name: dict[str, list[MaterializedArchive]] = defaultdict(list)
    for row in materialized:
        materialized_by_name[row.display_name.split("/")[-1].lower()].append(row)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    extracted: list[dict[str, Any]] = []
    blockers: list[str] = []
    for archive_id in sorted({by_resource[r]["archive_id"] for r in wanted if r in by_resource}):
        archive_meta = by_archive[archive_id]
        matches = materialized_by_name[archive_meta["archive_name"].lower()]
        if len(matches) != 1:
            blockers.append(f"archive-materialization-ambiguous:{archive_meta['archive_name']}:{len(matches)}")
            continue
        archive_wanted = {rid for rid in wanted if by_resource.get(rid, {}).get("archive_id") == archive_id}
        with BFF(matches[0].path) as archive:
            entries = {int(entry.index): entry for entry in archive.entries}
            for rid in sorted(archive_wanted):
                row = by_resource[rid]
                entry = entries.get(int(row["index"]))
                if entry is None or _norm(entry.path) != row["normalized_path"]:
                    blockers.append(f"catalog-entry-identity-mismatch:{rid}")
                    continue
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                except Exception as exc:
                    blockers.append(f"extract-failed:{rid}:{type(exc).__name__}")
                    continue
                relative = _safe_member(row["path"])
                target = out / archive_meta["archive_name"] / Path(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                extracted.append({
                    "resource_id": rid,
                    "archive": archive_meta["archive_name"],
                    "path": row["path"],
                    "output": str(target),
                    "decoded_size": len(payload),
                    "decoded_sha256": _sha256(payload),
                    "catalog_decoded_sha256": row.get("decoded_sha256"),
                    "identity_match": row.get("decoded_sha256") in (None, _sha256(payload)),
                })
    return {
        "format": "SHIFT.TypedResourceClosure/1",
        "version": 1,
        "status": "ready" if not blockers else "blocked",
        "ready": not blockers,
        "resource_count": len(wanted),
        "extracted_count": len(extracted),
        "resources": extracted,
        "blocking_reasons": blockers,
        "unresolved_dependencies": bootstrap.get("unresolved_dependencies") or [],
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_offline_pipeline(
    inputs: Sequence[str | Path],
    output_dir: str | Path,
    *,
    track: str,
    vehicle: str,
    decode_limit_per_archive: int = 0,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with materialize_bff_inputs(inputs) as materialized:
        catalog, graph, coverage = build_catalog(
            materialized,
            decode_known=True,
            decode_limit_per_archive=decode_limit_per_archive,
        )
        write_catalog_bundle(out, catalog, graph, coverage)
        bootstrap, admission = build_bootstrap_manifest(
            catalog, graph, track=track, vehicle=vehicle,
        )
        typed = extract_resource_closure(materialized, catalog, graph, bootstrap, out / "typed_resources")
        physics_report: dict[str, Any] | None = None
        vehicle_archive = (bootstrap.get("selected_archives") or {}).get("vehicle")
        if vehicle_archive is not None:
            matches = [
                row for row in materialized
                if row.display_name.split("/")[-1].lower() == vehicle_archive["archive_name"].lower()
            ]
            if len(matches) == 1:
                try:
                    from vehicle_physics_bundle import extract_bundle
                    physics_report = extract_bundle(matches[0].path, out / "vehicle_physics", strict=False)
                except Exception as exc:
                    physics_report = {
                        "format": "SHIFT.VehiclePhysicsBundleExtractor/1",
                        "ready": False,
                        "status": "blocked",
                        "error_kind": type(exc).__name__,
                        "error": str(exc),
                    }
        if physics_report is None:
            physics_report = {
                "format": "SHIFT.VehiclePhysicsBundleExtractor/1",
                "ready": False,
                "status": "blocked",
                "error": "selected vehicle archive unavailable",
            }
        _write_json(out / "scene_vehicle_bootstrap.json", bootstrap)
        _write_json(out / "typed_resource_closure.json", typed)
        _write_json(out / "native_runtime_admission.json", admission)
        _write_json(out / "vehicle_physics_bundle_report.json", physics_report)
        result = {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "version": 1,
            "status": "resource-ready-runtime-blocked" if bootstrap["ready"] else "resource-blocked",
            "resource_bootstrap_ready": bootstrap["ready"],
            "native_runtime_ready": False,
            "artifacts": {
                "catalog": str(out / "resource_catalog.json"),
                "dependency_graph": str(out / "dependency_graph.json"),
                "coverage": str(out / "coverage_report.json"),
                "bootstrap": str(out / "scene_vehicle_bootstrap.json"),
                "typed_resource_closure": str(out / "typed_resource_closure.json"),
                "native_admission": str(out / "native_runtime_admission.json"),
                "vehicle_physics": str(out / "vehicle_physics_bundle_report.json"),
            },
            "blocking_reasons": admission["blocking_reasons"],
            "boundary": admission["boundary"],
        }
        _write_json(out / "pipeline_run.json", result)
        return result
