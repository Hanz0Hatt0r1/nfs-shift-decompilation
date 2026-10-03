#!/usr/bin/env python3
"""Regenerate the renderer requirement audit from existing capture evidence.

This stage uses the historical raw D3D9 JSONL plus an exact Phase 618 ambiguity
report. It produces shader-use and texture/sampler evidence from that same
capture and feeds them, together with draw-local evidence, into the existing
fail-closed renderer requirement audit. No hard capture requirement is invented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.is_dir():
    paths = [SRC]
    paths.extend(
        sorted(
            (path for path in SRC.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.parts), str(path)),
        )
    )
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from d3d9_renderer_requirement_audit import build_renderer_requirement_audit
from d3d9_shader_use_evidence import build_shader_use_evidence
from d3d9_target_texture_sampler_evidence import (
    build_target_texture_sampler_evidence,
)

FORMAT = "SHIFT.SilverstoneRendererBaseAuditRegeneration/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
DRAW_LOCAL_FORMAT = "SHIFT.D3D9TargetDrawLocalEvidence/1"
AMBIGUITY_FORMAT = "SHIFT.IMBDrawLocalAmbiguityAudit/1"
BASE_AUDIT_FORMAT = "SHIFT.D3D9RendererRequirementAudit/1"
OUTPUT_NAMES = {
    "shader_use": "d3d9_shader_use_evidence.json",
    "texture_sampler": "d3d9_target_texture_sampler_evidence.json",
    "base_audit": "d3d9_renderer_requirement_audit.json",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> str:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temp = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)
    return hashlib.sha256(payload).hexdigest()


def _load_json(
    path: str | Path,
    *,
    expected_format: str,
    label: str,
) -> tuple[dict[str, Any], Mapping[str, Any] | None, list[str]]:
    source = Path(path).expanduser()
    record = {
        "path": str(source),
        "present": source.is_file(),
        "size": source.stat().st_size if source.is_file() else None,
        "sha256": _sha256_file(source) if source.is_file() else None,
        "expected_format": expected_format,
        "format": None,
    }
    blockers: list[str] = []
    if not source.is_file():
        blockers.append(f"input:{label}:file-not-found:{source}")
        return record, None, blockers
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except Exception as exc:
        blockers.append(
            f"input:{label}:json-read-failed:{type(exc).__name__}:{exc}"
        )
        return record, None, blockers
    if not isinstance(value, Mapping):
        blockers.append(f"input:{label}:json-root-not-object")
        return record, None, blockers
    record["format"] = value.get("format")
    if value.get("format") != expected_format:
        blockers.append(
            f"input:{label}:format-mismatch:{value.get('format')!r}"
        )
        return record, None, blockers
    return record, value, blockers


def _capture_record(path: str | Path) -> tuple[Path, dict[str, Any], list[str]]:
    source = Path(path).expanduser()
    record = {
        "path": str(source),
        "present": source.is_file(),
        "size": source.stat().st_size if source.is_file() else None,
        "sha256": _sha256_file(source) if source.is_file() else None,
    }
    blockers = [] if source.is_file() else [f"input:capture:file-not-found:{source}"]
    return source, record, blockers


def _stage(name: str, output: Path) -> dict[str, Any]:
    return {
        "name": name,
        "status": "pending",
        "output": str(output),
        "format": None,
        "sha256": None,
        "summary": None,
        "blocking_reasons": [],
    }


def _finish_stage(
    row: dict[str, Any],
    output: Path,
    report: Mapping[str, Any],
) -> None:
    row["status"] = "completed"
    row["format"] = report.get("format")
    row["sha256"] = _write_json_atomic(output, report)
    summary = report.get("summary")
    row["summary"] = dict(summary) if isinstance(summary, Mapping) else None


def regenerate_renderer_base_audit(
    *,
    capture_jsonl: str | Path,
    runtime_shader_targets: str | Path,
    draw_local: str | Path,
    ambiguity_audit: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    capture_path, capture, capture_blockers = _capture_record(capture_jsonl)
    target_record, targets, target_blockers = _load_json(
        runtime_shader_targets,
        expected_format=TARGET_FORMAT,
        label="runtime_shader_targets",
    )
    draw_record, draw_value, draw_blockers = _load_json(
        draw_local,
        expected_format=DRAW_LOCAL_FORMAT,
        label="draw_local",
    )
    ambiguity_record, ambiguity_value, ambiguity_blockers = _load_json(
        ambiguity_audit,
        expected_format=AMBIGUITY_FORMAT,
        label="ambiguity_audit",
    )
    blockers = [
        *capture_blockers,
        *target_blockers,
        *draw_blockers,
        *ambiguity_blockers,
    ]

    stages = {
        name: _stage(name, out / OUTPUT_NAMES[name])
        for name in ("shader_use", "texture_sampler", "base_audit")
    }
    shader_use: Mapping[str, Any] | None = None
    texture_sampler: Mapping[str, Any] | None = None
    base_audit: Mapping[str, Any] | None = None

    capture_and_targets_ready = capture_path.is_file() and targets is not None
    if not capture_and_targets_ready:
        reasons = []
        if not capture_path.is_file():
            reasons.append("capture-unavailable")
        if targets is None:
            reasons.append("runtime-shader-targets-unavailable")
        stages["shader_use"].update(
            status="blocked-missing-input",
            blocking_reasons=list(reasons),
        )
        stages["texture_sampler"].update(
            status="blocked-missing-input",
            blocking_reasons=list(reasons),
        )
    else:
        try:
            with capture_path.open("r", encoding="utf-8") as stream:
                shader_use = build_shader_use_evidence(
                    stream,
                    target_inventory=targets,
                )
            _finish_stage(
                stages["shader_use"],
                out / OUTPUT_NAMES["shader_use"],
                shader_use,
            )
        except Exception as exc:
            reason = f"{type(exc).__name__}:{exc}"
            stages["shader_use"].update(
                status="blocked-error",
                blocking_reasons=[reason],
            )
            blockers.append(f"shader_use:{reason}")

        try:
            with capture_path.open("r", encoding="utf-8") as stream:
                texture_sampler = build_target_texture_sampler_evidence(
                    stream,
                    target_inventory=targets,
                )
            _finish_stage(
                stages["texture_sampler"],
                out / OUTPUT_NAMES["texture_sampler"],
                texture_sampler,
            )
        except Exception as exc:
            reason = f"{type(exc).__name__}:{exc}"
            stages["texture_sampler"].update(
                status="blocked-error",
                blocking_reasons=[reason],
            )
            blockers.append(f"texture_sampler:{reason}")

    base_inputs_ready = all(
        value is not None
        for value in (shader_use, texture_sampler, draw_value, ambiguity_value)
    )
    if not base_inputs_ready:
        reasons = []
        if shader_use is None:
            reasons.append("shader-use-unavailable")
        if texture_sampler is None:
            reasons.append("texture-sampler-unavailable")
        if draw_value is None:
            reasons.append("draw-local-unavailable")
        if ambiguity_value is None:
            reasons.append("ambiguity-audit-unavailable")
        stages["base_audit"].update(
            status="blocked-missing-input",
            blocking_reasons=reasons,
        )
        blockers.extend(f"base_audit:{reason}" for reason in reasons)
    else:
        try:
            base_audit = build_renderer_requirement_audit(
                shader_use=shader_use,
                draw_local=draw_value,
                texture_sampler=texture_sampler,
                ambiguity=ambiguity_value,
                hard_requirements=(),
            )
            if base_audit.get("format") != BASE_AUDIT_FORMAT:
                raise ValueError(
                    f"unexpected base audit format {base_audit.get('format')!r}"
                )
            if (base_audit.get("summary") or {}).get("hard_requirement_count") not in (0, None):
                raise ValueError("base audit unexpectedly contains hard capture requirements")
            if (base_audit.get("summary") or {}).get("capture_required_now") is True:
                raise ValueError(
                    "base audit unexpectedly requires capture with no hard requirements"
                )
            _finish_stage(
                stages["base_audit"],
                out / OUTPUT_NAMES["base_audit"],
                base_audit,
            )
        except Exception as exc:
            reason = f"{type(exc).__name__}:{exc}"
            stages["base_audit"].update(
                status="blocked-error",
                blocking_reasons=[reason],
            )
            blockers.append(f"base_audit:{reason}")
            base_audit = None

    unique_blockers = list(dict.fromkeys(str(value) for value in blockers))
    completed = sum(row["status"] == "completed" for row in stages.values())
    ready = completed == 3 and base_audit is not None and not unique_blockers
    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "completed" if ready else "blocked",
        "ready": ready,
        "summary": {
            "completed_stage_count": completed,
            "blocked_stage_count": sum(
                str(row["status"]).startswith("blocked")
                for row in stages.values()
            ),
            "shader_use_available": shader_use is not None,
            "texture_sampler_available": texture_sampler is not None,
            "base_audit_available": base_audit is not None,
            "capture_required_now": (
                (base_audit.get("summary") or {}).get("capture_required_now") is True
                if isinstance(base_audit, Mapping)
                else False
            ),
        },
        "inputs": {
            "capture": capture,
            "runtime_shader_targets": target_record,
            "draw_local": draw_record,
            "ambiguity_audit": ambiguity_record,
        },
        "stages": [
            stages[name]
            for name in ("shader_use", "texture_sampler", "base_audit")
        ],
        "outputs": {
            "shader_use": (
                str(out / OUTPUT_NAMES["shader_use"])
                if shader_use is not None
                else None
            ),
            "texture_sampler": (
                str(out / OUTPUT_NAMES["texture_sampler"])
                if texture_sampler is not None
                else None
            ),
            "base_audit": (
                str(out / OUTPUT_NAMES["base_audit"])
                if base_audit is not None
                else None
            ),
        },
        "blocking_reasons": unique_blockers,
        "boundary": {
            "capture_source": "existing historical raw D3D9 JSONL",
            "shader_use_source": "raw create/set/draw history",
            "texture_sampler_source": "raw create/set-texture/sampler history",
            "ambiguity_source": "exact supplied SHIFT.IMBDrawLocalAmbiguityAudit/1",
            "hard_capture_requirements_supplied": [],
            "missing_capture_event_implies_recapture": False,
            "ranking_or_frequency_is_proof": False,
            "bundle_base_audit_required": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_base_audit_regeneration.json",
        manifest,
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-jsonl", required=True)
    parser.add_argument("--runtime-shader-targets", required=True)
    parser.add_argument("--draw-local", required=True)
    parser.add_argument("--ambiguity-audit", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    manifest = regenerate_renderer_base_audit(
        capture_jsonl=args.capture_jsonl,
        runtime_shader_targets=args.runtime_shader_targets,
        draw_local=args.draw_local,
        ambiguity_audit=args.ambiguity_audit,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "format": manifest["format"],
                "status": manifest["status"],
                "summary": manifest["summary"],
                "blocking_reasons": manifest["blocking_reasons"],
                "outputs": manifest["outputs"],
                "manifest": str(
                    Path(args.output_dir)
                    / "silverstone_renderer_base_audit_regeneration.json"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
