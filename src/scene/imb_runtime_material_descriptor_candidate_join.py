"""Join runtime D3D9 material texture descriptors to static IMB content candidates.

Phase 611 works per Phase 605 resource-shape signature rather than per geometry
shape. It only compares BMT-backed texture samplers that can be mapped through
the exact runtime pixel-shader CTAB sampler name/register contract. External
shadow/render-target/cube samplers are not treated as material DDS evidence.

Descriptor agreement is candidate-only evidence. Runtime resource path, payload
SHA and pointer identity remain unproven.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Iterable, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
_SOURCE_PATHS = [REPOSITORY_ROOT, SOURCE_ROOT]
if SOURCE_ROOT.is_dir():
    _SOURCE_PATHS.extend(
        sorted(
            (path for path in SOURCE_ROOT.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.parts), str(path)),
        )
    )
for _source_path in reversed(_SOURCE_PATHS):
    value = str(_source_path)
    if value not in sys.path:
        sys.path.insert(0, value)

from material_linker import parse_fx_samplers
from resource_formats import parse_bmt_material, parse_dds_metadata
from shader_ir import parse_shader_blobs
from shift_importer import BFF

FORMAT = "SHIFT.IMBRuntimeMaterialDescriptorCandidateJoin/1"
RUNTIME_FORMAT = "SHIFT.D3D9TargetDrawSignatureCatalog/1"
GEOMETRY_FORMAT = "SHIFT.IMBRuntimeGeometryShapeCandidateJoin/1"


def _norm(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def _valid_sha(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def resolve_input_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate
    repo_candidate = REPOSITORY_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate
    raise FileNotFoundError(
        f"input file not found: {candidate} "
        f"(also tried {repo_candidate})"
    )


def _materialize_bffs(
    inputs: Iterable[str | Path],
    stack: ExitStack,
) -> list[Path]:
    result: list[Path] = []
    for source in inputs:
        path = resolve_input_path(source)
        if path.suffix.lower() != ".zip":
            result.append(path)
            continue
        archive = zipfile.ZipFile(path)
        stack.callback(archive.close)
        root = Path(
            stack.enter_context(
                tempfile.TemporaryDirectory(prefix="shift-material-descriptor-")
            )
        )
        for name in archive.namelist():
            if name.endswith("/") or not name.lower().endswith(".bff"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            result.append(target)
    return result


def _fourcc_code(value: Any) -> int | None:
    text = str(value or "")
    if len(text) != 4:
        return None
    try:
        return int.from_bytes(text.encode("latin-1"), "little")
    except UnicodeEncodeError:
        return None


def _dds_descriptor(metadata: Mapping[str, Any]) -> dict[str, Any] | None:
    try:
        width = int(metadata.get("width"))
        height = int(metadata.get("height"))
        levels = int(metadata.get("mipmaps"))
    except (TypeError, ValueError):
        return None
    format_code = _fourcc_code(metadata.get("fourcc"))
    if width <= 0 or height <= 0 or levels <= 0 or format_code is None:
        return None
    return {
        "resource_type_name": "texture2d",
        "width": width,
        "height": height,
        "format": format_code,
        "level_count": levels,
    }


def _runtime_texture_descriptor(
    row: Mapping[str, Any],
) -> dict[str, Any] | None:
    if row.get("resource_type_name") != "texture2d":
        return None
    try:
        width = int(row.get("width"))
        height = int(row.get("height"))
        fmt = int(row.get("format"))
        levels = int(row.get("level_count"))
        stage = int(row.get("stage"))
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0 or levels <= 0 or stage < 0:
        return None
    return {
        "stage": stage,
        "resource_type_name": "texture2d",
        "width": width,
        "height": height,
        "format": fmt,
        "level_count": levels,
    }


def _descriptor_equal(
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> bool:
    return all(
        expected.get(key) == observed.get(key)
        for key in (
            "resource_type_name",
            "width",
            "height",
            "format",
            "level_count",
        )
    )


def _pixel_reflection_index(
    render_archive: BFF,
) -> dict[str, dict[str, Any]]:
    variants: dict[str, set[tuple[tuple[Any, ...], ...]]] = defaultdict(set)
    payload_seen: set[str] = set()

    for entry in render_archive.entries:
        if not _norm(entry.path).endswith(".fxo"):
            continue
        try:
            payload = render_archive.extract_entry(entry, type2="lzx")
        except Exception:
            continue
        payload_sha = hashlib.sha256(payload).hexdigest()
        if payload_sha in payload_seen:
            continue
        payload_seen.add(payload_sha)
        try:
            blobs = parse_shader_blobs(payload)
        except Exception:
            continue
        for blob in blobs:
            if blob.stage != "pixel":
                continue
            pixel_sha = hashlib.sha256(
                payload[blob.offset:blob.end]
            ).hexdigest()
            rows = []
            for sampler in blob.ctab_samplers:
                if not isinstance(sampler, Mapping):
                    continue
                try:
                    register = int(sampler.get("register"))
                    count = int(sampler.get("count", 1))
                except (TypeError, ValueError):
                    continue
                if register < 0 or count <= 0:
                    continue
                rows.append((
                    str(sampler.get("name") or ""),
                    register,
                    count,
                ))
            variants[pixel_sha].add(tuple(sorted(rows)))

    result: dict[str, dict[str, Any]] = {}
    for pixel_sha, signatures in variants.items():
        if len(signatures) != 1:
            result[pixel_sha] = {
                "status": "ambiguous",
                "variant_count": len(signatures),
                "samplers": [],
            }
            continue
        signature = next(iter(signatures))
        result[pixel_sha] = {
            "status": "consistent",
            "variant_count": 1,
            "samplers": [
                {"name": name, "register": register, "count": count}
                for name, register, count in signature
            ],
        }
    return result


def _render_fx_sources(render_archive: BFF) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for entry in render_archive.entries:
        key = _norm(entry.path)
        if not key.endswith(".fx"):
            continue
        try:
            payload = render_archive.extract_entry(entry, type2="lzx")
        except Exception:
            continue
        result.setdefault(key, payload)
    return result


def _build_material_occurrence_index(
    inputs: Iterable[str | Path],
    *,
    render_fx_sources: Mapping[str, bytes],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with ExitStack() as stack:
        paths = _materialize_bffs(inputs, stack)
        archives = [stack.enter_context(BFF(path)) for path in paths]

        for archive in archives:
            local: dict[str, list[Any]] = defaultdict(list)
            for entry in archive.entries:
                local[_norm(entry.path)].append(entry)

            dds_cache: dict[int, dict[str, Any] | None] = {}
            for entry in archive.entries:
                if not _norm(entry.path).endswith(".bmt"):
                    continue
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                    bmt_sha = hashlib.sha256(payload).hexdigest()
                    material = (
                        parse_bmt_material(payload).get("material") or {}
                    )
                except Exception:
                    continue

                shader_path = _norm(material.get("shader"))
                fx_source = render_fx_sources.get(shader_path)
                fx_samplers = (
                    parse_fx_samplers(fx_source)
                    if fx_source is not None
                    else []
                )
                params = {
                    str(row.get("name")): dict(row)
                    for row in (material.get("shaderparams") or [])
                    if isinstance(row, Mapping) and row.get("name")
                }

                texture_descriptors: dict[str, dict[str, Any]] = {}
                for texture in material.get("textures") or []:
                    texture_key = _norm(texture)
                    hits = local.get(texture_key, [])
                    if len(hits) != 1:
                        continue
                    tex_entry = hits[0]
                    cached = dds_cache.get(int(tex_entry.index))
                    if int(tex_entry.index) not in dds_cache:
                        try:
                            tex_payload = archive.extract_entry(
                                tex_entry,
                                type2="lzx",
                            )
                            cached = _dds_descriptor(
                                parse_dds_metadata(tex_payload)
                            )
                        except Exception:
                            cached = None
                        dds_cache[int(tex_entry.index)] = cached
                    if cached is not None:
                        texture_descriptors[texture_key] = dict(cached)

                result[bmt_sha].append({
                    "archive": archive.path.name,
                    "bmt_path": entry.path.replace("\\", "/"),
                    "bmt_sha256": bmt_sha,
                    "material_name": material.get("name"),
                    "shader": material.get("shader"),
                    "params": params,
                    "fx_samplers": {
                        str(row.get("sampler")): dict(row)
                        for row in fx_samplers
                        if row.get("sampler")
                    },
                    "texture_descriptors": texture_descriptors,
                })
    return dict(result)


def _material_contract(
    occurrence: Mapping[str, Any],
    *,
    pixel_sha: str | None,
    reflections: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    reflection = reflections.get(pixel_sha or "")
    if (
        not isinstance(reflection, Mapping)
        or reflection.get("status") != "consistent"
    ):
        return {
            "status": "reflection-unavailable",
            "bindings": [],
            "unresolved_material_sampler_count": 0,
        }

    params = occurrence.get("params") or {}
    fx_samplers = occurrence.get("fx_samplers") or {}
    textures = occurrence.get("texture_descriptors") or {}
    bindings: list[dict[str, Any]] = []
    unresolved = 0

    for reflected in reflection.get("samplers") or []:
        if not isinstance(reflected, Mapping):
            continue
        name = str(reflected.get("name") or "")
        fx = fx_samplers.get(name)
        if not isinstance(fx, Mapping):
            continue
        parameter = str(fx.get("texture_parameter") or "")
        param = params.get(parameter)
        if not isinstance(param, Mapping):
            continue
        value = param.get("value")
        if not isinstance(value, str) or not value.lower().endswith(".dds"):
            continue
        try:
            count = int(reflected.get("count", 1))
            register = int(reflected.get("register"))
        except (TypeError, ValueError):
            unresolved += 1
            continue
        if count != 1 or register < 0:
            unresolved += 1
            continue

        descriptor = textures.get(_norm(value))
        if not isinstance(descriptor, Mapping):
            unresolved += 1
            continue
        bindings.append({
            "sampler": name,
            "texture_parameter": parameter,
            "texture": value.replace("\\", "/"),
            "register": register,
            "descriptor": dict(descriptor),
        })

    return {
        "status": (
            "ready"
            if bindings and unresolved == 0
            else "incomplete"
        ),
        "bindings": sorted(
            bindings,
            key=lambda row: (
                int(row["register"]),
                str(row["sampler"]),
            ),
        ),
        "unresolved_material_sampler_count": unresolved,
    }


def _contract_matches_runtime(
    contract: Mapping[str, Any],
    runtime_stages: Mapping[int, Mapping[str, Any]],
) -> bool:
    if contract.get("status") != "ready":
        return False
    bindings = contract.get("bindings") or []
    if not bindings:
        return False
    for binding in bindings:
        try:
            register = int(binding.get("register"))
        except (TypeError, ValueError):
            return False
        expected = binding.get("descriptor")
        observed = runtime_stages.get(register)
        if (
            not isinstance(expected, Mapping)
            or not isinstance(observed, Mapping)
            or not _descriptor_equal(expected, observed)
        ):
            return False
    return True


def build_runtime_material_descriptor_candidate_join(
    runtime_catalog: Mapping[str, Any],
    geometry_join: Mapping[str, Any],
    *,
    material_occurrences: Mapping[str, list[dict[str, Any]]],
    pixel_reflections: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if runtime_catalog.get("format") != RUNTIME_FORMAT:
        raise ValueError(
            "runtime catalog must be "
            "SHIFT.D3D9TargetDrawSignatureCatalog/1"
        )
    if geometry_join.get("format") != GEOMETRY_FORMAT:
        raise ValueError(
            "geometry join must be "
            "SHIFT.IMBRuntimeGeometryShapeCandidateJoin/1"
        )

    geometry_by_resource: dict[str, Mapping[str, Any]] = {}
    for row in geometry_join.get("geometry_shapes") or []:
        if not isinstance(row, Mapping):
            continue
        for digest in row.get("resource_shape_sha256s") or []:
            if isinstance(digest, str):
                geometry_by_resource[digest] = row

    rows: list[dict[str, Any]] = []
    gate_status_counts: Counter[str] = Counter()
    single_count = 0
    single_draws = 0
    applied = 0
    reduced = 0
    fallback = 0
    ready_contract_rows = 0

    for resource in runtime_catalog.get("resource_shape_signatures") or []:
        if not isinstance(resource, Mapping):
            continue
        resource_sha = _valid_sha(resource.get("signature_sha256"))
        if not resource_sha:
            continue
        geometry = geometry_by_resource.get(resource_sha)
        if not isinstance(geometry, Mapping):
            continue

        signature = resource.get("signature") or {}
        runtime_stages = {}
        for stage_row in signature.get("texture_stages") or []:
            if not isinstance(stage_row, Mapping):
                continue
            descriptor = _runtime_texture_descriptor(stage_row)
            if descriptor is not None:
                runtime_stages[int(descriptor["stage"])] = descriptor

        base_groups = [
            dict(group)
            for group in (geometry.get("candidate_content_groups") or [])
            if isinstance(group, Mapping)
        ]
        evaluated: list[dict[str, Any]] = []
        matched: list[dict[str, Any]] = []

        for group in base_groups:
            bmt_sha = _valid_sha(group.get("bmt_sha256"))
            pixel_sha = _valid_sha(
                group.get("matched_pixel_shader_sha256")
                or signature.get("pixel_shader_sha256")
            )
            allowed_archives = {
                str(value)
                for value in (group.get("archives") or [])
                if value
            }
            occurrence_rows = [
                occurrence
                for occurrence in material_occurrences.get(
                    bmt_sha or "",
                    [],
                )
                if (
                    not allowed_archives
                    or str(occurrence.get("archive")) in allowed_archives
                )
            ]

            occurrence_evidence: list[dict[str, Any]] = []
            matching_occurrences = 0
            complete_occurrences = 0
            for occurrence in occurrence_rows:
                contract = _material_contract(
                    occurrence,
                    pixel_sha=pixel_sha,
                    reflections=pixel_reflections,
                )
                if contract.get("status") == "ready":
                    complete_occurrences += 1
                    ready_contract_rows += 1
                is_match = _contract_matches_runtime(
                    contract,
                    runtime_stages,
                )
                if is_match:
                    matching_occurrences += 1
                occurrence_evidence.append({
                    "archive": occurrence.get("archive"),
                    "bmt_path": occurrence.get("bmt_path"),
                    "material_name": occurrence.get("material_name"),
                    "shader": occurrence.get("shader"),
                    "contract_status": contract.get("status"),
                    "material_sampler_bindings": list(
                        contract.get("bindings") or []
                    ),
                    "unresolved_material_sampler_count": int(
                        contract.get(
                            "unresolved_material_sampler_count"
                        )
                        or 0
                    ),
                    "runtime_descriptor_match": is_match,
                })

            enriched = dict(group)
            enriched.update({
                "material_descriptor_complete_occurrence_count": (
                    complete_occurrences
                ),
                "material_descriptor_matching_occurrence_count": (
                    matching_occurrences
                ),
                "material_descriptor_match": matching_occurrences > 0,
                "material_occurrences": occurrence_evidence,
            })
            evaluated.append(enriched)
            if matching_occurrences > 0:
                matched.append(enriched)

        if matched:
            candidates = matched
            applied += 1
            if len(matched) < len(evaluated):
                reduced += 1
                gate_status = "reduced"
            else:
                gate_status = "matched-all"
        else:
            candidates = evaluated
            if any(
                int(group.get(
                    "material_descriptor_complete_occurrence_count"
                ) or 0) > 0
                for group in evaluated
            ):
                fallback += 1
                gate_status = "no-exact-match-fallback"
            else:
                gate_status = "not-applied"
        gate_status_counts[gate_status] += 1

        candidate_hashes = sorted({
            str(group.get("content_group_sha256"))
            for group in candidates
            if group.get("content_group_sha256")
        })
        if len(candidate_hashes) == 1:
            candidate_status = "single-content-candidate"
            single_count += 1
            single_draws += int(resource.get("draw_count") or 0)
        elif candidate_hashes:
            candidate_status = "ambiguous-content-candidates"
        elif not base_groups:
            candidate_status = "no-geometry-content-candidates"
        else:
            candidate_status = "no-content-candidates"

        rows.append({
            "resource_shape_sha256": resource_sha,
            "geometry_shape_sha256": geometry.get(
                "geometry_shape_sha256"
            ),
            "pipeline_signature_sha256": geometry.get(
                "pipeline_signature_sha256"
            ),
            "families": list(resource.get("families") or []),
            "draw_count": int(resource.get("draw_count") or 0),
            "first_frame": resource.get("first_frame"),
            "last_frame": resource.get("last_frame"),
            "runtime_texture_stages": [
                runtime_stages[key]
                for key in sorted(runtime_stages)
            ],
            "base_geometry_content_group_count": len(base_groups),
            "material_descriptor_gate_status": gate_status,
            "candidate_content_status": candidate_status,
            "candidate_content_group_count": len(candidate_hashes),
            "candidate_content_group_sha256s": candidate_hashes,
            "candidate_content_groups": candidates,
        })

    rows.sort(
        key=lambda row: (
            -int(row.get("draw_count") or 0),
            str(row.get("resource_shape_sha256") or ""),
        )
    )
    runtime_draws = sum(
        int(row.get("draw_count") or 0)
        for row in rows
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "not-observed",
        "summary": {
            "runtime_resource_shape_count": len(rows),
            "runtime_resource_shape_draw_count": runtime_draws,
            "material_descriptor_gate_applied_resource_shape_count": applied,
            "material_descriptor_gate_reduced_resource_shape_count": reduced,
            "material_descriptor_gate_fallback_resource_shape_count": fallback,
            "single_content_candidate_resource_shape_count": single_count,
            "single_content_candidate_draw_count": single_draws,
            "ready_material_occurrence_contract_count": ready_contract_rows,
            "material_descriptor_gate_status_counts": dict(
                sorted(gate_status_counts.items())
            ),
            "static_bmt_sha_count": len(material_occurrences),
            "pixel_reflection_sha_count": len(pixel_reflections),
        },
        "resource_shapes": rows,
        "boundary": {
            "candidate_only": True,
            "render_admission": False,
            "runtime_resource_identity": "not evaluated",
            "runtime_pointer_identity": "not preserved",
            "material_descriptor_gate": (
                "only BMT-backed DDS samplers mapped by FX sampler name and "
                "exact runtime pixel-shader CTAB register are compared; "
                "external samplers are ignored and zero-match rows fall back"
            ),
            "descriptor_fields": (
                "texture2d width + height + D3D9 format + mip level count"
            ),
            "single_content_candidate": (
                "one archive-invariant static content group survives runtime "
                "geometry + material descriptor narrowing; this is not exact "
                "DDS/IMB runtime resource identity"
            ),
            "required_for_promotion": (
                "exact runtime resource path/SHA or payload equality plus "
                "existing Phase 572 strong same-instance gates"
            ),
        },
    }


def validate_files(
    runtime_catalog_path: str | Path,
    geometry_join_path: str | Path,
    source_archive_path: str | Path,
    render_archive_path: str | Path,
) -> dict[str, Any]:
    runtime = json.loads(
        resolve_input_path(runtime_catalog_path).read_text(
            encoding="utf-8"
        )
    )
    geometry = json.loads(
        resolve_input_path(geometry_join_path).read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(runtime, dict) or not isinstance(geometry, dict):
        raise ValueError("runtime and geometry inputs must be JSON objects")

    render_path = resolve_input_path(render_archive_path)
    with BFF(render_path) as render:
        fx_sources = _render_fx_sources(render)
        reflections = _pixel_reflection_index(render)

    occurrences = _build_material_occurrence_index(
        [source_archive_path],
        render_fx_sources=fx_sources,
    )
    return build_runtime_material_descriptor_candidate_join(
        runtime,
        geometry,
        material_occurrences=occurrences,
        pixel_reflections=reflections,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_catalog")
    parser.add_argument("geometry_join")
    parser.add_argument("source_archive")
    parser.add_argument("render_archive")
    parser.add_argument("output")
    args = parser.parse_args(argv)

    report = validate_files(
        args.runtime_catalog,
        args.geometry_join,
        args.source_archive,
        args.render_archive,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
