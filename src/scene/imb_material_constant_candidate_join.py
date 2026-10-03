"""Narrow Phase 618 material ambiguity with exact BMT -> CTAB -> draw constants.

This stage never ranks candidates.  A draw becomes single-candidate only when one
candidate has at least one complete source-backed material constant match and
every other surviving candidate is contradicted by complete evidence.  Missing
BMTs, missing FXO provenance, optimized-out parameters, or incomplete runtime
constant state retain ambiguity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
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

from resource_formats import parse_bmt_material
from shift_importer import BFF
from uniform_linker import link_material_uniforms

FORMAT = "SHIFT.IMBMaterialConstantCandidateJoin/1"
AMBIGUITY_FORMAT = "SHIFT.IMBDrawLocalAmbiguityAudit/1"
DRAW_FORMAT = "SHIFT.D3D9TargetDrawLocalEvidence/1"
FXO_FORMAT = "SHIFT.IMBFXOPairProvenance/1"
_NUMERIC_TYPES = {"EPT_F32", "EPT_VEC2", "EPT_VEC3", "EPT_VEC4", "EPT_INT", "EPT_BOOL"}


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


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _f32_bits(value: Any) -> str | None:
    try:
        return struct.pack("<f", float(value)).hex()
    except (TypeError, ValueError, OverflowError, struct.error):
        return None


def _numeric_components(value: Any) -> list[Any] | None:
    if isinstance(value, bool):
        return [1.0 if value else 0.0]
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, (list, tuple)) and value:
        result = list(value)
        if all(isinstance(item, (bool, int, float)) for item in result):
            return result
    return None


def resolve_input_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate
    repo_candidate = REPOSITORY_ROOT / candidate
    if repo_candidate.exists():
        return repo_candidate
    raise FileNotFoundError(
        f"input file not found: {candidate} (also tried {repo_candidate})"
    )


def _materialize_bffs(
    inputs: Iterable[str | Path],
    stack: ExitStack,
) -> list[tuple[Path, str]]:
    result: list[tuple[Path, str]] = []
    for source in inputs:
        path = resolve_input_path(source)
        if path.suffix.lower() != ".zip":
            result.append((path, str(path)))
            continue
        archive = zipfile.ZipFile(path)
        stack.callback(archive.close)
        root = Path(
            stack.enter_context(
                tempfile.TemporaryDirectory(prefix="shift-material-constant-")
            )
        )
        for name in archive.namelist():
            if name.endswith("/") or not name.lower().endswith(".bff"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            result.append((target, f"{path}::{name.replace(chr(92), '/') }"))
    return result


def _wanted_bmt_hashes(ambiguity: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for draw in ambiguity.get("ambiguous_draws") or []:
        if not isinstance(draw, Mapping) or draw.get("ambiguity_class") != "material-distinct-candidates":
            continue
        for candidate in draw.get("candidates") or []:
            if not isinstance(candidate, Mapping):
                continue
            digest = _valid_sha(candidate.get("bmt_sha256"))
            if digest:
                result.add(digest)
    return result


def load_materials_by_sha(
    inputs: Iterable[str | Path],
    wanted_hashes: set[str],
) -> dict[str, dict[str, Any]]:
    """Load only BMT payloads needed by the Phase 618 material ambiguity set."""
    result: dict[str, dict[str, Any]] = {}
    if not wanted_hashes:
        return result
    with ExitStack() as stack:
        for path, source_input in _materialize_bffs(inputs, stack):
            try:
                archive = stack.enter_context(BFF(path))
            except Exception:
                continue
            for entry in archive.entries:
                if not _norm(entry.path).endswith(".bmt"):
                    continue
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                except Exception:
                    continue
                digest = hashlib.sha256(payload).hexdigest()
                if digest not in wanted_hashes:
                    continue
                group = result.setdefault(digest, {
                    "bmt_sha256": digest,
                    "payload": payload,
                    "material": None,
                    "parse_status": "not-parsed",
                    "occurrences": [],
                })
                group["occurrences"].append({
                    "source_input": source_input,
                    "archive": archive.path.name,
                    "entry_path": str(entry.path).replace("\\", "/"),
                    "entry_index": int(entry.index),
                })
                if group["material"] is None:
                    try:
                        group["material"] = parse_bmt_material(payload).get("material") or {}
                        group["parse_status"] = "parsed"
                    except Exception as exc:
                        group["parse_status"] = "parse-error"
                        group["parse_error"] = f"{type(exc).__name__}: {exc}"
    for group in result.values():
        group["occurrences"].sort(
            key=lambda row: (
                str(row.get("source_input") or "").lower(),
                str(row.get("archive") or "").lower(),
                str(row.get("entry_path") or "").lower(),
                int(row.get("entry_index") or -1),
            )
        )
    return result


def _verified_fxo_requirements(
    fxo_report: Mapping[str, Any],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    if fxo_report.get("format") != FXO_FORMAT:
        raise ValueError(f"FXO provenance must be {FXO_FORMAT}")
    result: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for variant in fxo_report.get("variants") or []:
        if not isinstance(variant, Mapping) or int(variant.get("verified_occurrence_count") or 0) <= 0:
            continue
        vertex = _valid_sha(variant.get("vertex_byte_sha256"))
        pixel = _valid_sha(variant.get("pixel_byte_sha256"))
        if not vertex or not pixel:
            continue
        allowed_payloads = {
            _valid_sha((check.get("provenance") or {}).get("payload_sha256"))
            for check in (variant.get("occurrence_checks") or [])
            if isinstance(check, Mapping) and check.get("status") == "verified-exact-fxo-pair"
        }
        allowed_payloads.discard(None)
        if not allowed_payloads:
            continue
        result[(vertex, pixel)].append({
            "candidate_file": str(variant.get("candidate_file") or "").replace("\\", "/"),
            "vertex_program_offset": variant.get("candidate_vertex_program_offset"),
            "pixel_program_offset": variant.get("candidate_program_offset"),
            "allowed_payload_sha256s": sorted(allowed_payloads),
            "variant_provenance_sha256": variant.get("variant_provenance_sha256"),
        })
    return dict(result)


def load_verified_fxo_pairs(
    inputs: Iterable[str | Path],
    fxo_report: Mapping[str, Any],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    requirements = _verified_fxo_requirements(fxo_report)
    wanted_files = {
        _norm(row.get("candidate_file"))
        for rows in requirements.values()
        for row in rows
        if row.get("candidate_file")
    }
    loaded: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with ExitStack() as stack:
        for path, source_input in _materialize_bffs(inputs, stack):
            try:
                archive = stack.enter_context(BFF(path))
            except Exception:
                continue
            for entry in archive.entries:
                key = _norm(entry.path)
                if key not in wanted_files:
                    continue
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                except Exception:
                    continue
                loaded[key].append({
                    "payload": payload,
                    "payload_sha256": hashlib.sha256(payload).hexdigest(),
                    "source_input": source_input,
                    "archive": archive.path.name,
                    "entry_path": str(entry.path).replace("\\", "/"),
                    "entry_index": int(entry.index),
                })

    result: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[Any, ...]] = set()
    for pair, rows in requirements.items():
        for requirement in rows:
            file_key = _norm(requirement.get("candidate_file"))
            allowed = set(requirement.get("allowed_payload_sha256s") or [])
            for occurrence in loaded.get(file_key, []):
                if occurrence.get("payload_sha256") not in allowed:
                    continue
                key = (
                    pair,
                    occurrence.get("payload_sha256"),
                    requirement.get("vertex_program_offset"),
                    requirement.get("pixel_program_offset"),
                )
                if key in seen:
                    continue
                seen.add(key)
                result[pair].append({
                    **occurrence,
                    "vertex_program_offset": requirement.get("vertex_program_offset"),
                    "pixel_program_offset": requirement.get("pixel_program_offset"),
                    "variant_provenance_sha256": requirement.get("variant_provenance_sha256"),
                })
    return dict(result)


def _runtime_variables(draw: Mapping[str, Any], stage: str) -> dict[tuple[str, int, int], Mapping[str, Any]]:
    snapshot = draw.get(f"{stage}_constants") or {}
    result = {}
    for row in snapshot.get("variables") or []:
        if not isinstance(row, Mapping):
            continue
        name = str(row.get("name") or "")
        register_index = row.get("register_index")
        register_count = row.get("register_count")
        if name and isinstance(register_index, int) and isinstance(register_count, int):
            result[(name, register_index, register_count)] = row
    return result


def _runtime_components(variable: Mapping[str, Any]) -> list[Any] | None:
    if variable.get("complete") is not True:
        return None
    values: list[Any] = []
    registers = variable.get("registers") or []
    for row in registers:
        if not isinstance(row, Mapping):
            return None
        register_values = row.get("values")
        if not isinstance(register_values, list) or len(register_values) != 4:
            return None
        values.extend(register_values)
    return values


def evaluate_material_constant_contract(
    material: Mapping[str, Any],
    fxo_bytes: bytes,
    *,
    vertex_offset: int,
    pixel_offset: int,
    draw: Mapping[str, Any],
) -> dict[str, Any]:
    linked = link_material_uniforms(
        dict(material),
        fxo_bytes,
        [int(vertex_offset), int(pixel_offset)],
    )
    runtime = {
        "vertex": _runtime_variables(draw, "vertex"),
        "pixel": _runtime_variables(draw, "pixel"),
    }
    witnesses: list[dict[str, Any]] = []
    matched = contradicted = insufficient = 0

    for binding in linked.get("bindings") or []:
        if not isinstance(binding, Mapping) or binding.get("binding") != "material-constant":
            continue
        param_type = str(binding.get("type") or "").upper()
        if param_type not in _NUMERIC_TYPES:
            continue
        expected_values = _numeric_components(binding.get("value"))
        if not expected_values:
            continue
        stage = str(binding.get("stage") or "")
        register_index = binding.get("register_index")
        register_count = binding.get("register_count")
        component_count = binding.get("component_count")
        if stage not in runtime or not isinstance(register_index, int) or not isinstance(register_count, int):
            continue
        try:
            component_count = int(component_count)
        except (TypeError, ValueError):
            component_count = len(expected_values)
        key = (str(binding.get("name") or ""), register_index, register_count)
        observed_variable = runtime[stage].get(key)
        observed_values = _runtime_components(observed_variable or {}) if observed_variable else None
        base = {
            "name": binding.get("name"),
            "stage": stage,
            "type": param_type,
            "register_index": register_index,
            "register_count": register_count,
            "component_count": component_count,
            "expected_values": list(expected_values),
            "expected_f32_bits": [_f32_bits(value) for value in expected_values],
        }
        if observed_values is None or len(observed_values) < component_count:
            insufficient += 1
            witnesses.append({
                **base,
                "status": "incomplete-runtime-constant",
                "observed_values": None,
                "observed_f32_bits": None,
            })
            continue
        observed = list(observed_values[:component_count])
        expected = list(expected_values[:component_count])
        expected_bits = [_f32_bits(value) for value in expected]
        observed_bits = [_f32_bits(value) for value in observed]
        if None in expected_bits or None in observed_bits:
            insufficient += 1
            status = "non-f32-comparable-value"
        elif expected_bits == observed_bits:
            matched += 1
            status = "exact-f32-match"
        else:
            contradicted += 1
            status = "exact-f32-contradiction"
        witnesses.append({
            **base,
            "status": status,
            "observed_values": observed,
            "observed_f32_bits": observed_bits,
        })

    comparable = matched + contradicted
    if contradicted:
        status = "exact-material-constant-contradiction"
        confidence = "exact-f32-ctab-register-contradiction"
    elif matched and not insufficient:
        status = "exact-material-constant-match"
        confidence = "exact-f32-ctab-register-match"
    else:
        status = "insufficient-material-constant-evidence"
        confidence = "none"
    return {
        "status": status,
        "confidence": confidence,
        "matched_witness_count": matched,
        "contradicted_witness_count": contradicted,
        "insufficient_witness_count": insufficient,
        "comparable_witness_count": comparable,
        "witnesses": witnesses,
        "optimized_out_or_unreflected": list(linked.get("optimized_out_or_unreflected") or []),
    }


def _candidate_pair(candidate: Mapping[str, Any]) -> tuple[str, str] | None:
    vertex = _valid_sha(candidate.get("matched_vertex_shader_sha256"))
    pixel = _valid_sha(candidate.get("matched_pixel_shader_sha256"))
    return (vertex, pixel) if vertex and pixel else None


def evaluate_candidate(
    candidate: Mapping[str, Any],
    draw: Mapping[str, Any],
    *,
    materials_by_sha: Mapping[str, Mapping[str, Any]],
    fxo_pairs: Mapping[tuple[str, str], list[Mapping[str, Any]]],
) -> dict[str, Any]:
    bmt_sha = _valid_sha(candidate.get("bmt_sha256"))
    pair = _candidate_pair(candidate)
    base = {
        "content_group_sha256": _valid_sha(candidate.get("content_group_sha256")),
        "bmt_sha256": bmt_sha,
        "shader_pair": {
            "vertex_shader_sha256": pair[0] if pair else None,
            "pixel_shader_sha256": pair[1] if pair else None,
        },
        "imb_sha256": _valid_sha(candidate.get("imb_sha256")),
        "imb_paths": list(candidate.get("imb_paths") or []),
        "archives": list(candidate.get("archives") or []),
    }
    material_row = materials_by_sha.get(bmt_sha or "")
    if not isinstance(material_row, Mapping) or material_row.get("parse_status") != "parsed":
        return {
            **base,
            "status": "insufficient-material-constant-evidence",
            "confidence": "none",
            "blocking_reasons": ["exact-bmt-payload-not-available"],
            "contracts": [],
        }
    if pair is None:
        return {
            **base,
            "status": "insufficient-material-constant-evidence",
            "confidence": "none",
            "blocking_reasons": ["exact-shader-pair-not-available"],
            "contracts": [],
        }
    pair_rows = list(fxo_pairs.get(pair) or [])
    if not pair_rows:
        return {
            **base,
            "status": "insufficient-material-constant-evidence",
            "confidence": "none",
            "blocking_reasons": ["verified-fxo-pair-payload-not-available"],
            "contracts": [],
        }

    contracts = []
    for pair_row in pair_rows:
        payload = pair_row.get("payload")
        try:
            vertex_offset = int(pair_row.get("vertex_program_offset"))
            pixel_offset = int(pair_row.get("pixel_program_offset"))
        except (TypeError, ValueError):
            continue
        if not isinstance(payload, (bytes, bytearray)):
            continue
        contract = evaluate_material_constant_contract(
            material_row.get("material") or {},
            bytes(payload),
            vertex_offset=vertex_offset,
            pixel_offset=pixel_offset,
            draw=draw,
        )
        contracts.append({
            **contract,
            "fxo_provenance": {
                key: pair_row.get(key)
                for key in (
                    "source_input", "archive", "entry_path", "entry_index",
                    "payload_sha256", "vertex_program_offset", "pixel_program_offset",
                    "variant_provenance_sha256",
                )
                if pair_row.get(key) is not None
            },
        })

    statuses = {str(row.get("status")) for row in contracts}
    contract_signatures = {
        _canonical_hash({
            "status": row.get("status"),
            "witnesses": [
                {
                    key: witness.get(key)
                    for key in (
                        "name", "stage", "register_index", "register_count",
                        "component_count", "expected_f32_bits", "observed_f32_bits", "status",
                    )
                }
                for witness in (row.get("witnesses") or [])
            ],
        })
        for row in contracts
    }
    blockers: list[str] = []
    if not contracts:
        status = "insufficient-material-constant-evidence"
        confidence = "none"
        blockers.append("no-evaluable-fxo-contract")
    elif len(contract_signatures) != 1:
        status = "insufficient-material-constant-evidence"
        confidence = "none"
        blockers.append("equivalent-fxo-provenance-produced-different-constant-contracts")
    elif statuses == {"exact-material-constant-match"}:
        status = "exact-material-constant-match"
        confidence = "exact-f32-ctab-register-match"
    elif "exact-material-constant-contradiction" in statuses:
        status = "exact-material-constant-contradiction"
        confidence = "exact-f32-ctab-register-contradiction"
    else:
        status = "insufficient-material-constant-evidence"
        confidence = "none"
        blockers.append("material-constant-contract-incomplete")

    return {
        **base,
        "status": status,
        "confidence": confidence,
        "blocking_reasons": blockers,
        "bmt_occurrences": list(material_row.get("occurrences") or []),
        "contract_count": len(contracts),
        "contracts": contracts,
    }


def build_material_constant_candidate_join(
    ambiguity: Mapping[str, Any],
    draw_local: Mapping[str, Any],
    *,
    materials_by_sha: Mapping[str, Mapping[str, Any]],
    fxo_pairs: Mapping[tuple[str, str], list[Mapping[str, Any]]],
) -> dict[str, Any]:
    if ambiguity.get("format") != AMBIGUITY_FORMAT:
        raise ValueError(f"ambiguity report must be {AMBIGUITY_FORMAT}")
    if draw_local.get("format") != DRAW_FORMAT:
        raise ValueError(f"draw-local report must be {DRAW_FORMAT}")

    draws_by_event = {
        row.get("event_index"): row
        for row in (draw_local.get("draws") or [])
        if isinstance(row, Mapping) and isinstance(row.get("event_index"), int)
    }
    rows = []
    status_counts: Counter[str] = Counter()
    candidate_status_counts: Counter[str] = Counter()

    for ambiguity_row in ambiguity.get("ambiguous_draws") or []:
        if not isinstance(ambiguity_row, Mapping) or ambiguity_row.get("ambiguity_class") != "material-distinct-candidates":
            continue
        event_index = ambiguity_row.get("event_index")
        draw = draws_by_event.get(event_index)
        candidates = [
            candidate for candidate in (ambiguity_row.get("candidates") or [])
            if isinstance(candidate, Mapping)
        ]
        if draw is None:
            candidate_results = []
            resolution = "draw-local-evidence-missing"
            blockers = ["target-draw-not-found-by-event-index"]
        else:
            candidate_results = [
                evaluate_candidate(
                    candidate,
                    draw,
                    materials_by_sha=materials_by_sha,
                    fxo_pairs=fxo_pairs,
                )
                for candidate in candidates
            ]
            for result in candidate_results:
                candidate_status_counts[str(result.get("status"))] += 1
            matches = [
                result for result in candidate_results
                if result.get("status") == "exact-material-constant-match"
            ]
            contradictions = [
                result for result in candidate_results
                if result.get("status") == "exact-material-constant-contradiction"
            ]
            insufficient = [
                result for result in candidate_results
                if result.get("status") == "insufficient-material-constant-evidence"
            ]
            blockers = []
            if len(matches) == 1 and len(contradictions) == len(candidate_results) - 1 and not insufficient:
                resolution = "single-candidate-by-exact-material-constants"
            elif len(matches) > 1:
                resolution = "ambiguous-multiple-exact-material-constant-matches"
            elif matches and insufficient:
                resolution = "ambiguous-unexcluded-candidates"
            elif not matches and contradictions and not insufficient:
                resolution = "material-constant-conflict-no-survivor"
                blockers.append("all-candidates-contradicted-retain-original-set")
            else:
                resolution = "insufficient-material-constant-evidence"
        status_counts[resolution] += 1
        selected = None
        if resolution == "single-candidate-by-exact-material-constants":
            selected = next(
                result for result in candidate_results
                if result.get("status") == "exact-material-constant-match"
            )
        rows.append({
            "event_index": event_index,
            "frame": ambiguity_row.get("frame"),
            "draw_evidence_sha256": _valid_sha(ambiguity_row.get("draw_evidence_sha256")),
            "candidate_set_sha256": _valid_sha(ambiguity_row.get("candidate_set_sha256")),
            "input_candidate_count": len(candidates),
            "resolution_status": resolution,
            "blocking_reasons": blockers,
            "selected_content_group_sha256": (
                selected.get("content_group_sha256") if selected else None
            ),
            "candidate_results": candidate_results,
        })

    rows.sort(key=lambda row: (
        int(row["event_index"]) if isinstance(row.get("event_index"), int) else 2**63 - 1,
        str(row.get("candidate_set_sha256") or ""),
    ))
    resolved_count = sum(
        row.get("resolution_status") == "single-candidate-by-exact-material-constants"
        for row in rows
    )
    return {
        "format": FORMAT,
        "version": 1,
        "status": "observed" if rows else "no-material-distinct-candidates",
        "summary": {
            "material_distinct_draw_count": len(rows),
            "single_candidate_draw_count": resolved_count,
            "remaining_ambiguous_draw_count": len(rows) - resolved_count,
            "resolution_status_counts": dict(sorted(status_counts.items())),
            "candidate_status_counts": dict(sorted(candidate_status_counts.items())),
            "loaded_bmt_identity_count": len(materials_by_sha),
            "verified_fxo_pair_identity_count": len(fxo_pairs),
        },
        "draws": rows,
        "boundary": {
            "proof_chain": (
                "exact BMT payload SHA -> parsed numeric shader parameter -> exact verified "
                "FXO VS/PS pair -> CTAB float register -> complete draw-local constant state"
            ),
            "numeric_equality": "IEEE-754 float32 bit equality after source/runtime numeric conversion",
            "selection_rule": (
                "one exact match is accepted only when every other surviving candidate is "
                "explicitly contradicted by complete exact evidence"
            ),
            "insufficient_policy": "an unobserved/incomplete candidate is never eliminated",
            "all_contradicted_policy": "retain the original candidate set and report conflict",
            "ranking_policy": "ranking is not proof and is not used by this stage",
            "texture_gate": "BMT/DDS sampler identity remains independent and may further narrow unresolved rows",
            "render_admission": False,
            "capture_requirement": "none; this stage consumes existing draw-local constant writes",
        },
    }


def build_report(
    ambiguity: Mapping[str, Any],
    draw_local: Mapping[str, Any],
    fxo_report: Mapping[str, Any],
    corpus: Iterable[str | Path],
) -> dict[str, Any]:
    wanted_bmts = _wanted_bmt_hashes(ambiguity)
    materials = load_materials_by_sha(corpus, wanted_bmts)
    fxo_pairs = load_verified_fxo_pairs(corpus, fxo_report)
    report = build_material_constant_candidate_join(
        ambiguity,
        draw_local,
        materials_by_sha=materials,
        fxo_pairs=fxo_pairs,
    )
    report["corpus_inputs"] = [str(value) for value in corpus]
    report["wanted_bmt_sha256s"] = sorted(wanted_bmts)
    report["missing_bmt_sha256s"] = sorted(wanted_bmts - set(materials))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ambiguity_audit")
    parser.add_argument("draw_local_evidence")
    parser.add_argument("fxo_pair_provenance")
    parser.add_argument("output")
    parser.add_argument("--corpus", action="append", required=True)
    args = parser.parse_args(argv)

    ambiguity = json.loads(resolve_input_path(args.ambiguity_audit).read_text(encoding="utf-8"))
    draw_local = json.loads(resolve_input_path(args.draw_local_evidence).read_text(encoding="utf-8"))
    fxo_report = json.loads(resolve_input_path(args.fxo_pair_provenance).read_text(encoding="utf-8"))
    report = build_report(ambiguity, draw_local, fxo_report, args.corpus)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
