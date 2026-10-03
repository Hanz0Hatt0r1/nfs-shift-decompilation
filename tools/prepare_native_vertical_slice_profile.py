#!/usr/bin/env python3
"""Prepare a fail-closed native vertical-slice profile from runtime requirements."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if SRC.is_dir():
    paths = [SRC]
    paths.extend(sorted(
        (path for path in SRC.rglob("*") if path.is_dir()),
        key=lambda path: (len(path.parts), str(path)),
    ))
    for path in reversed(paths):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from offline_vertical_slice_profile import build_vertical_slice_profile_prepare


def _load(path: str | Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirements", help="SHIFT.OfflineNativeRuntimeRequirements/1 JSON")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("-o", "--output", required=True, help="profile JSON path")
    parser.add_argument("--report", help="prepare-report JSON path")
    for option in (
        "scene-set",
        "camera-state",
        "physics-manifest",
        "participant-boundary",
        "solver-frame",
        "generated-body-constraint-frame",
        "constraint-sample-relation-frame",
        "constraint-relation-reset-frame",
        "post-solve-projection",
    ):
        parser.add_argument("--" + option)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--input-script")
    mode.add_argument("--interactive", action="store_true")
    mode.add_argument("--keyboard", action="store_true")
    parser.add_argument("--frames", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile_path = Path(args.output)
    report_path = Path(args.report) if args.report else profile_path.with_suffix(
        profile_path.suffix + ".prepare.json"
    )
    explicit = {
        "scene_set": args.scene_set,
        "camera_state": args.camera_state,
        "physics_manifest": args.physics_manifest,
        "participant_boundary": args.participant_boundary,
        "solver_frame": args.solver_frame,
        "generated_body_constraint_frame": args.generated_body_constraint_frame,
        "constraint_sample_relation_frame": args.constraint_sample_relation_frame,
        "constraint_relation_reset_frame": args.constraint_relation_reset_frame,
        "post_solve_projection": args.post_solve_projection,
    }
    report = build_vertical_slice_profile_prepare(
        _load(args.requirements),
        workspace_root=args.workspace_root,
        profile_path=profile_path,
        explicit_inputs=explicit,
        input_script=args.input_script,
        interactive=args.interactive,
        keyboard=args.keyboard,
        frames=args.frames,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if report["ready"]:
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            json.dumps(report["profile"], ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    elif profile_path.exists():
        profile_path.unlink()

    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "auto_filled_inputs": report["auto_filled_inputs"],
        "explicit_filled_inputs": report["explicit_filled_inputs"],
        "blocking_reasons": report["blocking_reasons"],
        "profile": str(profile_path) if report["ready"] else None,
        "report": str(report_path),
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
