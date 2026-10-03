#!/usr/bin/env python3
"""Run renderer production directly from source corpus plus historical capture.

Phase 637 regenerates the full runtime shader target set before delegating to the
Phase 635 self-bootstrap path. Renderer report bundles are optional canonical
cross-check inputs; when none are supplied an internal empty ZIP records that no
bundle cross-check evidence was provided.

When an exact OfflineRuntimeBootstrap report is supplied, Phase 638 reuses its
hashed static scene artifacts to regenerate the optional Phase 595 OBJECT
candidate join against the newly rebuilt capture pipeline. No manual candidate
join JSON is required on that path.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from run_silverstone_renderer_self_bootstrap_production import (
    run_self_bootstrap_production,
)
from run_silverstone_renderer_shader_target_regeneration import (
    regenerate_full_shader_target_set,
)

FORMAT = "SHIFT.SilverstoneRendererSourceBootstrapProductionRun/1"
TARGET_FORMAT = "SHIFT.IMBRuntimeShaderTargetSet/1"
DEFAULT_COMPACT_EVIDENCE = (
    ROOT / "evidence" / "silverstone_era3_runtime_shader_targets.json"
)


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
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


def _empty_crosscheck_bundle(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED):
        pass
    return path


def _load_json_map(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"JSON object expected: {path}")
    return value


def _validate_prebuilt_target(
    path: Path,
) -> tuple[Mapping[str, Any] | None, list[str]]:
    blockers: list[str] = []
    if not path.is_file():
        return None, [f"file-not-found:{path}"]
    try:
        value = _load_json_map(path)
    except Exception as exc:
        return None, [f"unreadable:{type(exc).__name__}:{exc}"]
    if value.get("format") != TARGET_FORMAT:
        blockers.append(
            f"format-mismatch:{value.get('format')!r}:expected-{TARGET_FORMAT}"
        )
    if value.get("capture_ready") is not True:
        blockers.append("not-capture-ready")
    bindings = value.get("binding_targets")
    if not isinstance(bindings, list) or not bindings:
        blockers.append("binding-targets-empty-or-missing")
    return (value if not blockers else None), blockers


def run_source_bootstrap_production(
    *,
    capture_jsonl: str | Path,
    output_dir: str | Path,
    corpus: list[str | Path],
    bundles: list[str | Path] | None = None,
    pe_evidence: str | Path | None = None,
    pe_image: str | Path | None = None,
    runtime_shader_targets: str | Path | None = None,
    runtime_bootstrap: str | Path | None = None,
    compact_evidence: str | Path | None = None,
    compact_crosscheck: bool = True,
    max_json_bytes: int = 128 * 1024 * 1024,
) -> dict[str, Any]:
    if (pe_evidence is None) == (pe_image is None):
        raise ValueError("exactly one of pe_evidence or pe_image is required")

    out = Path(output_dir)
    target_dir = out / "shader-targets"
    self_dir = out / "self-bootstrap"
    internal_dir = out / "internal"
    blockers: list[str] = []

    target_manifest: Mapping[str, Any] | None = None
    target_path: str | None = None
    target_mode: str

    if runtime_shader_targets is not None:
        target_mode = "explicit-prebuilt"
        prebuilt = Path(runtime_shader_targets).expanduser()
        _value, target_blockers = _validate_prebuilt_target(prebuilt)
        blockers.extend(
            f"runtime_shader_targets:{reason}" for reason in target_blockers
        )
        if not target_blockers:
            target_path = str(prebuilt)
    else:
        target_mode = "regenerated-from-corpus"
        compact_path: str | Path | None
        if not compact_crosscheck:
            compact_path = None
        elif compact_evidence is not None:
            compact_path = compact_evidence
        else:
            compact_path = DEFAULT_COMPACT_EVIDENCE

        try:
            target_manifest = regenerate_full_shader_target_set(
                corpus=corpus,
                output_dir=target_dir,
                compact_evidence=compact_path,
            )
        except Exception as exc:
            blockers.append(
                f"shader_target_regeneration:failed:{type(exc).__name__}:{exc}"
            )
            target_manifest = None
        if isinstance(target_manifest, Mapping):
            blockers.extend(
                f"shader_target_regeneration:{reason}"
                for reason in (target_manifest.get("blocking_reasons") or [])
            )
            outputs = target_manifest.get("outputs")
            if isinstance(outputs, Mapping) and outputs.get("runtime_shader_targets"):
                target_path = str(outputs["runtime_shader_targets"])
        if not target_path:
            blockers.append("shader_target_regeneration:target-set-unavailable")

    bundle_inputs = list(bundles or [])
    synthetic_empty_bundle = False
    if not bundle_inputs:
        synthetic_empty_bundle = True
        bundle_inputs = [
            _empty_crosscheck_bundle(
                internal_dir / "empty_renderer_crosscheck_bundle.zip"
            )
        ]

    self_manifest: Mapping[str, Any] | None = None
    self_started = bool(target_path) and not blockers
    if self_started:
        try:
            self_manifest = run_self_bootstrap_production(
                bundles=bundle_inputs,
                capture_jsonl=capture_jsonl,
                pe_evidence=pe_evidence,
                pe_image=pe_image,
                output_dir=self_dir,
                corpus=corpus,
                runtime_shader_targets=target_path,
                runtime_bootstrap=runtime_bootstrap,
                max_json_bytes=max_json_bytes,
            )
        except Exception as exc:
            blockers.append(
                f"self_bootstrap:failed:{type(exc).__name__}:{exc}"
            )
            self_manifest = None
        if isinstance(self_manifest, Mapping):
            blockers.extend(
                f"self_bootstrap:{reason}"
                for reason in (self_manifest.get("blocking_reasons") or [])
            )

    blockers = list(dict.fromkeys(str(value) for value in blockers))
    self_ready = (
        isinstance(self_manifest, Mapping)
        and self_manifest.get("ready") is True
    )
    ready = self_ready and not blockers

    object_join = (
        self_manifest.get("object_candidate_join")
        if isinstance(self_manifest, Mapping)
        and isinstance(self_manifest.get("object_candidate_join"), Mapping)
        else None
    )
    manifest = {
        "format": FORMAT,
        "version": 1,
        "status": "completed" if ready else "blocked",
        "ready": ready,
        "summary": {
            "shader_target_mode": target_mode,
            "shader_target_regeneration_ready": (
                target_mode == "explicit-prebuilt"
                or (
                    isinstance(target_manifest, Mapping)
                    and target_manifest.get("ready") is True
                )
            ),
            "bundle_crosscheck_supplied": not synthetic_empty_bundle,
            "runtime_bootstrap_supplied": runtime_bootstrap is not None,
            "object_candidate_join_regeneration_ready": (
                object_join.get("regeneration_ready") is True
                if isinstance(object_join, Mapping)
                else False
            ),
            "self_bootstrap_started": self_started,
            "self_bootstrap_ready": self_ready,
            "production_completed": (
                isinstance(self_manifest, Mapping)
                and isinstance(self_manifest.get("production"), Mapping)
                and self_manifest["production"].get("status") == "completed"
            ),
            "blocking_reason_count": len(blockers),
        },
        "shader_targets": {
            "mode": target_mode,
            "path": target_path,
            "regeneration_format": (
                target_manifest.get("format")
                if isinstance(target_manifest, Mapping)
                else None
            ),
            "regeneration_status": (
                target_manifest.get("status")
                if isinstance(target_manifest, Mapping)
                else None
            ),
            "regeneration_summary": (
                target_manifest.get("summary")
                if isinstance(target_manifest, Mapping)
                else None
            ),
            "regeneration_manifest": (
                str(
                    target_dir
                    / "silverstone_renderer_shader_target_regeneration.json"
                )
                if isinstance(target_manifest, Mapping)
                else None
            ),
        },
        "bundle_crosscheck": {
            "user_supplied": not synthetic_empty_bundle,
            "inputs": [
                str(Path(value).expanduser()) for value in (bundles or [])
            ],
            "effective_inputs": [str(Path(value)) for value in bundle_inputs],
            "synthetic_empty_bundle": synthetic_empty_bundle,
            "synthetic_empty_bundle_contains_evidence": False,
        },
        "resource_scene_evidence": {
            "runtime_bootstrap": (
                str(Path(runtime_bootstrap).expanduser())
                if runtime_bootstrap is not None
                else None
            ),
            "object_candidate_join": (
                dict(object_join) if isinstance(object_join, Mapping) else None
            ),
        },
        "self_bootstrap": {
            "format": (
                self_manifest.get("format")
                if isinstance(self_manifest, Mapping)
                else None
            ),
            "status": (
                self_manifest.get("status")
                if isinstance(self_manifest, Mapping)
                else None
            ),
            "summary": (
                self_manifest.get("summary")
                if isinstance(self_manifest, Mapping)
                else None
            ),
            "production": (
                self_manifest.get("production")
                if isinstance(self_manifest, Mapping)
                else None
            ),
            "manifest": (
                str(
                    self_dir
                    / "silverstone_renderer_self_bootstrap_production_run.json"
                )
                if self_started
                else None
            ),
        },
        "blocking_reasons": blockers,
        "boundary": {
            "dependency_order": (
                "Phase636 full shader targets -> Phase630 -> Phase638 optional "
                "object join -> Phase634 -> Phase633 -> Phase619-626"
            ),
            "manual_full_shader_target_handoff_required": False,
            "manual_renderer_report_bundle_required": False,
            "manual_object_candidate_join_handoff_required_when_runtime_bootstrap_supplied": False,
            "runtime_bootstrap_scene_artifacts_are_hash_verified_before_object_join": True,
            "bundle_inputs_are_crosscheck_only": True,
            "synthetic_empty_bundle_is_evidence": False,
            "compact_phase568_evidence_is_crosscheck_only": True,
            "unique_scene_candidate_is_render_admission": False,
            "ranking_or_frequency_is_proof": False,
            "original_game_execution_required": False,
            "new_capture_required": False,
        },
    }
    _write_json_atomic(
        out / "silverstone_renderer_source_bootstrap_production_run.json",
        manifest,
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-jsonl", required=True)
    pe = parser.add_mutually_exclusive_group(required=True)
    pe.add_argument("--pe-evidence")
    pe.add_argument("--pe-image")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--corpus", action="append", default=[])
    parser.add_argument("--bundle", action="append", default=[])
    parser.add_argument("--runtime-shader-targets")
    parser.add_argument("--runtime-bootstrap")
    parser.add_argument("--compact-evidence")
    parser.add_argument("--no-compact-crosscheck", action="store_true")
    parser.add_argument(
        "--max-json-bytes",
        type=int,
        default=128 * 1024 * 1024,
    )
    args = parser.parse_args(argv)

    manifest = run_source_bootstrap_production(
        capture_jsonl=args.capture_jsonl,
        pe_evidence=args.pe_evidence,
        pe_image=args.pe_image,
        output_dir=args.output_dir,
        corpus=args.corpus,
        bundles=args.bundle,
        runtime_shader_targets=args.runtime_shader_targets,
        runtime_bootstrap=args.runtime_bootstrap,
        compact_evidence=args.compact_evidence,
        compact_crosscheck=not args.no_compact_crosscheck,
        max_json_bytes=args.max_json_bytes,
    )
    print(json.dumps({
        "format": manifest["format"],
        "status": manifest["status"],
        "summary": manifest["summary"],
        "blocking_reasons": manifest["blocking_reasons"],
        "renderer_frontier": (
            ((manifest.get("self_bootstrap") or {}).get("production") or {}).get(
                "renderer_frontier"
            )
        ),
        "manifest": str(
            Path(args.output_dir)
            / "silverstone_renderer_source_bootstrap_production_run.json"
        ),
    }, ensure_ascii=False, indent=2))
    return 0 if manifest["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
