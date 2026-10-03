"""Verify static FXO VS/PS byte-pair provenance without ranking candidates.

The input target set already carries candidate FXO entry paths, program offsets,
and expected shader hashes.  This stage reopens the supplied offline corpus and
checks those claims against the exact embedded shader bytes.  Multiple matching
copies remain multiple provenance locations; no candidate is selected by order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from collections import defaultdict
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

from shader_ir import parse_shader_blobs
from shader_permutation_identity import build_shader_permutation_identity
from shift_importer import BFF

FORMAT = "SHIFT.IMBFXOPairProvenance/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
AMBIGUITY_FORMAT = "SHIFT.IMBDrawLocalAmbiguityAudit/1"


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
                tempfile.TemporaryDirectory(prefix="shift-fxo-provenance-")
            )
        )
        for name in archive.namelist():
            if name.endswith("/") or not name.lower().endswith(".bff"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            result.append((target, f"{path}::{name.replace(chr(92), '/') }"))
    return result


def _flatten_variants(target_set: Mapping[str, Any]) -> list[dict[str, Any]]:
    if target_set.get("format") != TARGET_FORMAT:
        raise ValueError(f"target set must be {TARGET_FORMAT}")
    rows: list[dict[str, Any]] = []
    for binding in target_set.get("binding_targets") or []:
        if not isinstance(binding, Mapping):
            continue
        for target_index, target in enumerate(binding.get("targets") or []):
            if not isinstance(target, Mapping):
                continue
            variants = [
                value
                for value in (target.get("candidate_variants") or [])
                if isinstance(value, Mapping)
            ]
            if not variants:
                variants = [target]
            for variant_index, variant in enumerate(variants):
                rows.append({
                    "binding_index": binding.get("binding_index"),
                    "target_index": target_index,
                    "variant_index": variant_index,
                    "target_identity_kind": target.get("identity_kind"),
                    "target_identity_value": target.get("identity_value"),
                    "target_strength": target.get("strength"),
                    "candidate_file": variant.get("candidate_file") or target.get("candidate_file"),
                    "candidate_program_offset": variant.get("candidate_program_offset")
                    if variant.get("candidate_program_offset") is not None
                    else target.get("candidate_program_offset"),
                    "candidate_vertex_program_offset": variant.get("candidate_vertex_program_offset")
                    if variant.get("candidate_vertex_program_offset") is not None
                    else target.get("candidate_vertex_program_offset"),
                    "vertex_byte_sha256": _valid_sha(
                        variant.get("vertex_byte_sha256")
                        or target.get("vertex_byte_sha256")
                    ),
                    "pixel_byte_sha256": _valid_sha(
                        variant.get("pixel_byte_sha256")
                        or target.get("pixel_byte_sha256")
                    ),
                    "pair_byte_sha256": _valid_sha(
                        variant.get("pair_byte_sha256")
                        or target.get("pair_byte_sha256")
                    ),
                    "permutation_identity_sha256": _valid_sha(
                        variant.get("permutation_identity_sha256")
                        or target.get("permutation_identity_sha256")
                    ),
                    "source_exact_flag": variant.get("exact") is True,
                })
    return rows


def _required_pairs_from_ambiguity(
    ambiguity: Mapping[str, Any] | None,
) -> set[tuple[str, str]] | None:
    if ambiguity is None:
        return None
    if ambiguity.get("format") != AMBIGUITY_FORMAT:
        raise ValueError(f"ambiguity audit must be {AMBIGUITY_FORMAT}")
    pairs: set[tuple[str, str]] = set()
    for draw in ambiguity.get("ambiguous_draws") or []:
        if not isinstance(draw, Mapping):
            continue
        if draw.get("ambiguity_class") != "shader-provenance-distinct-candidates":
            continue
        for candidate in draw.get("candidates") or []:
            if not isinstance(candidate, Mapping):
                continue
            vertex = _valid_sha(candidate.get("matched_vertex_shader_sha256"))
            pixel = _valid_sha(candidate.get("matched_pixel_shader_sha256"))
            if vertex and pixel:
                pairs.add((vertex, pixel))
    return pairs


def candidate_files(
    target_set: Mapping[str, Any],
    ambiguity: Mapping[str, Any] | None = None,
) -> list[str]:
    required = _required_pairs_from_ambiguity(ambiguity)
    names = set()
    for row in _flatten_variants(target_set):
        pair = (row.get("vertex_byte_sha256"), row.get("pixel_byte_sha256"))
        if required is not None and pair not in required:
            continue
        name = str(row.get("candidate_file") or "").replace("\\", "/")
        if name:
            names.add(name)
    return sorted(names, key=str.lower)


def load_candidate_occurrences(
    inputs: Iterable[str | Path],
    wanted_files: Iterable[str],
) -> dict[str, list[dict[str, Any]]]:
    wanted = {_norm(value) for value in wanted_files if value}
    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not wanted:
        return {}
    with ExitStack() as stack:
        materialized = _materialize_bffs(inputs, stack)
        for path, source_input in materialized:
            try:
                archive = stack.enter_context(BFF(path))
            except Exception as exc:
                continue
            for entry in archive.entries:
                key = _norm(entry.path)
                if key not in wanted:
                    continue
                base = {
                    "source_input": source_input,
                    "archive": archive.path.name,
                    "entry_path": str(entry.path).replace("\\", "/"),
                    "entry_index": int(entry.index),
                }
                try:
                    payload = archive.extract_entry(entry, type2="lzx")
                except Exception as exc:
                    occurrences[key].append({
                        **base,
                        "payload": None,
                        "load_status": "extract-error",
                        "error_kind": type(exc).__name__,
                        "error": str(exc),
                    })
                    continue
                occurrences[key].append({
                    **base,
                    "payload": payload,
                    "payload_sha256": hashlib.sha256(payload).hexdigest(),
                    "load_status": "loaded",
                })
    for rows in occurrences.values():
        rows.sort(
            key=lambda row: (
                str(row.get("source_input") or "").lower(),
                str(row.get("archive") or "").lower(),
                str(row.get("entry_path") or "").lower(),
                int(row.get("entry_index") or -1),
            )
        )
    return dict(occurrences)


def _offset(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def verify_variant_occurrence(
    variant: Mapping[str, Any],
    occurrence: Mapping[str, Any],
) -> dict[str, Any]:
    provenance = {
        key: occurrence.get(key)
        for key in ("source_input", "archive", "entry_path", "entry_index", "payload_sha256")
        if occurrence.get(key) is not None
    }
    payload = occurrence.get("payload")
    if not isinstance(payload, (bytes, bytearray)):
        return {
            "status": "payload-unavailable",
            "confidence": "none",
            "provenance": provenance,
            "blocking_reasons": [str(occurrence.get("load_status") or "payload-unavailable")],
            "actual": {},
            "mismatches": [],
        }

    vertex_offset = _offset(variant.get("candidate_vertex_program_offset"))
    pixel_offset = _offset(variant.get("candidate_program_offset"))
    blockers: list[str] = []
    if vertex_offset is None:
        blockers.append("vertex-program-offset-missing")
    if pixel_offset is None:
        blockers.append("pixel-program-offset-missing")
    expected_vertex = _valid_sha(variant.get("vertex_byte_sha256"))
    expected_pixel = _valid_sha(variant.get("pixel_byte_sha256"))
    if expected_vertex is None:
        blockers.append("expected-vertex-byte-sha256-missing")
    if expected_pixel is None:
        blockers.append("expected-pixel-byte-sha256-missing")
    if blockers:
        return {
            "status": "insufficient-provenance-contract",
            "confidence": "none",
            "provenance": provenance,
            "blocking_reasons": blockers,
            "actual": {},
            "mismatches": [],
        }

    try:
        blobs = parse_shader_blobs(bytes(payload))
    except Exception as exc:
        return {
            "status": "fxo-parse-error",
            "confidence": "none",
            "provenance": provenance,
            "blocking_reasons": [f"{type(exc).__name__}: {exc}"],
            "actual": {},
            "mismatches": [],
        }
    by_offset = {int(blob.offset): blob for blob in blobs}
    vertex_blob = by_offset.get(vertex_offset)
    pixel_blob = by_offset.get(pixel_offset)
    if vertex_blob is None or vertex_blob.stage != "vertex":
        blockers.append("vertex-program-offset-not-vertex-blob")
    if pixel_blob is None or pixel_blob.stage != "pixel":
        blockers.append("pixel-program-offset-not-pixel-blob")
    if blockers:
        return {
            "status": "program-offset-mismatch",
            "confidence": "none",
            "provenance": provenance,
            "blocking_reasons": blockers,
            "actual": {},
            "mismatches": [],
        }

    vertex_bytes = bytes(payload)[vertex_blob.offset:vertex_blob.end]
    pixel_bytes = bytes(payload)[pixel_blob.offset:pixel_blob.end]
    actual_vertex = hashlib.sha256(vertex_bytes).hexdigest()
    actual_pixel = hashlib.sha256(pixel_bytes).hexdigest()
    actual_pair = hashlib.sha256(vertex_bytes + pixel_bytes).hexdigest()
    actual_permutation = None
    permutation_error = None
    try:
        identity = build_shader_permutation_identity(
            bytes(payload),
            vertex_offset=vertex_offset,
            pixel_offset=pixel_offset,
        )
        actual_permutation = _valid_sha(identity.get("identity_sha256"))
    except Exception as exc:
        permutation_error = f"{type(exc).__name__}: {exc}"

    expected = {
        "vertex_byte_sha256": expected_vertex,
        "pixel_byte_sha256": expected_pixel,
        "pair_byte_sha256": _valid_sha(variant.get("pair_byte_sha256")),
        "permutation_identity_sha256": _valid_sha(
            variant.get("permutation_identity_sha256")
        ),
    }
    actual = {
        "vertex_byte_sha256": actual_vertex,
        "pixel_byte_sha256": actual_pixel,
        "pair_byte_sha256": actual_pair,
        "permutation_identity_sha256": actual_permutation,
        "vertex_program_offset": vertex_offset,
        "pixel_program_offset": pixel_offset,
        "vertex_byte_size": len(vertex_bytes),
        "pixel_byte_size": len(pixel_bytes),
    }
    mismatches = []
    for key in ("vertex_byte_sha256", "pixel_byte_sha256", "pair_byte_sha256"):
        if expected[key] is not None and expected[key] != actual[key]:
            mismatches.append(key)
    if expected["permutation_identity_sha256"] is not None:
        if actual_permutation is None:
            blockers.append("permutation-identity-recompute-failed")
        elif expected["permutation_identity_sha256"] != actual_permutation:
            mismatches.append("permutation_identity_sha256")

    verified = not blockers and not mismatches
    return {
        "status": "verified-exact-fxo-pair" if verified else "byte-identity-mismatch",
        "confidence": "exact-byte-equality" if verified else "none",
        "provenance": provenance,
        "blocking_reasons": blockers,
        "mismatches": mismatches,
        "expected": expected,
        "actual": actual,
        "permutation_identity_error": permutation_error,
    }


def audit_target_set(
    target_set: Mapping[str, Any],
    occurrences: Mapping[str, list[Mapping[str, Any]]],
    *,
    ambiguity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    required_pairs = _required_pairs_from_ambiguity(ambiguity)
    variants = _flatten_variants(target_set)
    selected: list[dict[str, Any]] = []
    for row in variants:
        pair = (row.get("vertex_byte_sha256"), row.get("pixel_byte_sha256"))
        if required_pairs is not None and pair not in required_pairs:
            continue
        selected.append(row)

    variant_rows: list[dict[str, Any]] = []
    verified_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    for variant in selected:
        file_key = _norm(variant.get("candidate_file"))
        hits = list(occurrences.get(file_key) or []) if file_key else []
        checks = [verify_variant_occurrence(variant, occurrence) for occurrence in hits]
        verified = [row for row in checks if row.get("status") == "verified-exact-fxo-pair"]
        verified_payloads = {
            str((row.get("provenance") or {}).get("payload_sha256"))
            for row in verified
            if (row.get("provenance") or {}).get("payload_sha256")
        }
        if not file_key:
            provenance_status = "candidate-file-missing"
        elif not hits:
            provenance_status = "candidate-file-not-found-in-corpus"
        elif not verified:
            provenance_status = "no-byte-exact-occurrence"
        elif len(verified) == 1:
            provenance_status = "exact-source-occurrence"
        elif len(verified_payloads) == 1:
            provenance_status = "content-equivalent-multiple-source-occurrences"
        else:
            provenance_status = "exact-pair-multiple-payload-provenance"

        variant_id = _canonical_hash({
            key: variant.get(key)
            for key in (
                "binding_index", "target_index", "variant_index",
                "candidate_file", "candidate_program_offset",
                "candidate_vertex_program_offset", "vertex_byte_sha256",
                "pixel_byte_sha256", "pair_byte_sha256",
                "permutation_identity_sha256",
            )
        })
        variant_rows.append({
            **variant,
            "variant_provenance_sha256": variant_id,
            "provenance_status": provenance_status,
            "source_occurrence_count": len(hits),
            "verified_occurrence_count": len(verified),
            "occurrence_checks": checks,
        })

        for check in verified:
            actual = check.get("actual") or {}
            vertex = _valid_sha(actual.get("vertex_byte_sha256"))
            pixel = _valid_sha(actual.get("pixel_byte_sha256"))
            if not vertex or not pixel:
                continue
            key = (vertex, pixel)
            group = verified_pairs.setdefault(key, {
                "vertex_shader_sha256": vertex,
                "pixel_shader_sha256": pixel,
                "pair_byte_sha256": _valid_sha(actual.get("pair_byte_sha256")),
                "permutation_identity_sha256s": set(),
                "source_occurrences": {},
                "variant_provenance_sha256s": set(),
            })
            permutation = _valid_sha(actual.get("permutation_identity_sha256"))
            if permutation:
                group["permutation_identity_sha256s"].add(permutation)
            provenance = dict(check.get("provenance") or {})
            provenance_key = _canonical_hash(provenance)
            group["source_occurrences"][provenance_key] = provenance
            group["variant_provenance_sha256s"].add(variant_id)

    pair_rows = []
    for group in verified_pairs.values():
        pair_rows.append({
            "vertex_shader_sha256": group["vertex_shader_sha256"],
            "pixel_shader_sha256": group["pixel_shader_sha256"],
            "pair_byte_sha256": group["pair_byte_sha256"],
            "permutation_identity_sha256s": sorted(group["permutation_identity_sha256s"]),
            "source_occurrence_count": len(group["source_occurrences"]),
            "source_occurrences": [
                group["source_occurrences"][key]
                for key in sorted(group["source_occurrences"])
            ],
            "variant_provenance_sha256s": sorted(group["variant_provenance_sha256s"]),
            "proof_status": "verified-exact-fxo-pair",
            "confidence": "exact-byte-equality",
        })
    pair_rows.sort(key=lambda row: (row["vertex_shader_sha256"], row["pixel_shader_sha256"]))

    covered_pairs = set(verified_pairs)
    missing_required = sorted((required_pairs or set()) - covered_pairs)
    if required_pairs is None:
        status = "verified" if variant_rows and all(
            row.get("verified_occurrence_count", 0) > 0 for row in variant_rows
        ) else ("partial" if variant_rows else "empty")
        ready = status == "verified"
    elif not required_pairs:
        status = "no-shader-provenance-distinct-candidates"
        ready = True
    else:
        ready = not missing_required
        status = "required-pairs-verified" if ready else "required-pairs-partial"

    return {
        "format": FORMAT,
        "version": 1,
        "status": status,
        "ready": ready,
        "source_target_format": target_set.get("format"),
        "ambiguity_filter": {
            "enabled": required_pairs is not None,
            "source_format": ambiguity.get("format") if ambiguity is not None else None,
            "required_pair_count": len(required_pairs or set()),
            "required_pairs": [
                {"vertex_shader_sha256": vertex, "pixel_shader_sha256": pixel}
                for vertex, pixel in sorted(required_pairs or set())
            ],
        },
        "summary": {
            "input_variant_count": len(variants),
            "audited_variant_count": len(variant_rows),
            "verified_variant_count": sum(
                row.get("verified_occurrence_count", 0) > 0 for row in variant_rows
            ),
            "unverified_variant_count": sum(
                row.get("verified_occurrence_count", 0) == 0 for row in variant_rows
            ),
            "verified_pair_count": len(pair_rows),
            "missing_required_pair_count": len(missing_required),
        },
        "missing_required_pairs": [
            {"vertex_shader_sha256": vertex, "pixel_shader_sha256": pixel}
            for vertex, pixel in missing_required
        ],
        "verified_pairs": pair_rows,
        "variants": variant_rows,
        "boundary": {
            "proof": (
                "exact embedded FXO VS/PS bytes at explicit program offsets, "
                "recomputed from supplied offline corpus"
            ),
            "multiple_copy_policy": (
                "byte-identical or pair-identical source occurrences remain listed; "
                "archive/file order never selects one"
            ),
            "ranking_policy": "ranking is not proof and is not used for selection",
            "runtime_claim": (
                "this proves static FXO pair provenance only; runtime draw identity still "
                "comes from exact capture shader byte hashes"
            ),
            "capture_requirement": "none",
        },
    }


def build_report(
    target_set: Mapping[str, Any],
    corpus: Iterable[str | Path],
    *,
    ambiguity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    wanted = candidate_files(target_set, ambiguity)
    occurrences = load_candidate_occurrences(corpus, wanted)
    report = audit_target_set(target_set, occurrences, ambiguity=ambiguity)
    report["corpus_inputs"] = [str(value) for value in corpus]
    report["candidate_file_count"] = len(wanted)
    report["candidate_files"] = wanted
    report["corpus_occurrence_count"] = sum(len(rows) for rows in occurrences.values())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_set")
    parser.add_argument("output")
    parser.add_argument("--corpus", action="append", required=True)
    parser.add_argument("--ambiguity-audit")
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)

    target_set = json.loads(resolve_input_path(args.target_set).read_text(encoding="utf-8"))
    ambiguity = None
    if args.ambiguity_audit:
        ambiguity = json.loads(
            resolve_input_path(args.ambiguity_audit).read_text(encoding="utf-8")
        )
    report = build_report(target_set, args.corpus, ambiguity=ambiguity)
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "summary": report["summary"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] or not args.require_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
