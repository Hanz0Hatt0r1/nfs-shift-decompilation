#!/usr/bin/env python3
"""Validate and launch a playable composite scene backed by a resource pipeline.

This wrapper preserves the existing native vertical-slice launcher as the
resource/runtime authority. It first builds the ordinary resource-pipeline launch
plan, then re-proves that one ready Phase 643 composite scene derives from the
exact pipeline scene before replacing only the scene-set argument.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
RESOURCES = ROOT / "src" / "resources"
for path in (TOOLS, RESOURCES):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import run_native_vertical_slice as native
from resource_pipeline_playable_scene_join import (
    build_resource_pipeline_playable_scene_join,
)


def build_playable_pipeline_launch_plan(
    profile_path: str | Path,
    *,
    runtime: str | Path = "native_runtime/build/shift_runtime",
    validation: bool = False,
) -> dict[str, Any]:
    profile_path = Path(profile_path).resolve()
    profile = native._load_json(profile_path, label="vertical-slice profile")
    if profile.get("resource_pipeline") in (None, ""):
        raise native.ProfileError("playable pipeline profile requires resource_pipeline")
    if profile.get("playable_scene_bootstrap") in (None, ""):
        raise native.ProfileError(
            "playable pipeline profile requires playable_scene_bootstrap"
        )

    plan = native.build_launch_plan(
        profile_path,
        runtime=runtime,
        validation=validation,
    )
    workspace_root = Path(plan["workspace_root"]).resolve()
    pipeline_root = Path(str(plan.get("resource_pipeline") or "")).resolve()
    playable_bootstrap = native._resolve_member(
        workspace_root,
        profile.get("playable_scene_bootstrap"),
        label="playable_scene_bootstrap",
    )

    try:
        join = build_resource_pipeline_playable_scene_join(
            workspace_root=workspace_root,
            resource_pipeline=pipeline_root,
            playable_scene_bootstrap=playable_bootstrap,
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise native.ProfileError(
            "playable resource-pipeline scene provenance invalid: " + str(exc)
        ) from exc
    if join.get("ready") is not True:
        raise native.ProfileError("playable resource-pipeline scene provenance is not ready")

    composite = native._resolve_recorded_member(
        workspace_root,
        (join.get("composite_scene") or {}).get("path"),
        label="playable composite scene set",
    )
    composite_check = native._validate_scene_set(composite)

    argv = list(plan["argv"])
    scene_indices = [index for index, value in enumerate(argv) if value == "--scene-set"]
    if len(scene_indices) != 1 or scene_indices[0] + 1 >= len(argv):
        raise native.ProfileError("base launch plan does not contain one scene-set argument")
    argv[scene_indices[0] + 1] = str(composite)

    checks = dict(plan.get("checks") or {})
    checks["source_scene_set"] = dict(checks.get("scene_set") or {})
    checks["scene_set"] = {
        **composite_check,
        "source": "proven-resource-pipeline-playable-composite",
    }
    checks["resource_pipeline_playable_scene_join"] = join

    boundary = dict(plan.get("boundary") or {})
    boundary.update({
        "scene_and_physics_from_resource_pipeline": False,
        "physics_and_participant_from_resource_pipeline": True,
        "resource_pipeline_source_scene_directly_submitted": False,
        "playable_composite_scene_provenance_revalidated": True,
        "playable_composite_scene_submitted": True,
        "resource_pipeline_playable_scene_join_is_runtime_execution_proof": False,
    })

    result = dict(plan)
    result["argv"] = argv
    result["checks"] = checks
    result["boundary"] = boundary
    result["playable_scene_bootstrap"] = str(playable_bootstrap)
    result["playable_scene_mode"] = "proven-resource-pipeline-derived-composite"
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", help=f"{native.PROFILE_FORMAT} JSON profile")
    parser.add_argument(
        "--runtime",
        default="native_runtime/build/shift_runtime",
        help="native runtime executable, workspace-relative unless absolute",
    )
    parser.add_argument("--validation", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json-out")
    args = parser.parse_args(argv)

    try:
        plan = build_playable_pipeline_launch_plan(
            args.profile,
            runtime=args.runtime,
            validation=args.validation,
        )
    except (OSError, native.ProfileError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")

    if args.dry_run:
        return 0
    launch_environment = os.environ.copy()
    launch_environment.update(plan["environment"])
    completed = subprocess.run(plan["argv"], env=launch_environment, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
