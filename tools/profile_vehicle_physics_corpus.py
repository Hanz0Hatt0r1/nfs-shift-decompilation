#!/usr/bin/env python3
"""Decode and profile base vehicle physics resources across a BFF corpus.

Only archives that contain both a physics CDF and EDF are selected. The
canonical vehicle_physics_bundle extractor remains responsible for exact target
resolution and all downstream physics parsers; this tool only orchestrates the
corpus pass and records per-vehicle results.
"""
from __future__ import annotations

import argparse
import json
from contextlib import ExitStack
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from shift_importer import BFF
from vehicle_physics_bundle import extract_bundle


def _materialize_bffs(
    inputs: Iterable[str | Path],
    stack: ExitStack,
) -> list[Path]:
    paths: list[Path] = []
    for source in inputs:
        path = Path(source)
        if path.suffix.lower() != ".zip":
            paths.append(path)
            continue

        archive = zipfile.ZipFile(path)
        stack.callback(archive.close)
        root = Path(
            stack.enter_context(
                tempfile.TemporaryDirectory(prefix="shift-physics-corpus-")
            )
        )
        for name in archive.namelist():
            if not name.lower().endswith(".bff") or name.endswith("/"):
                continue
            target = root / Path(name).name
            target.write_bytes(archive.read(name))
            paths.append(target)
    return paths


def _has_base_physics(path: Path) -> bool:
    with BFF(path) as archive:
        normalized = [
            entry.path.replace(chr(92), "/").lower()
            for entry in archive.entries
        ]
    return (
        any(item.endswith(".cdf") and "/physics/" in item for item in normalized)
        and any(item.endswith(".edf") and "/physics/" in item for item in normalized)
    )


def profile_vehicle_physics_corpus(
    inputs: Iterable[str | Path],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    with ExitStack() as stack:
        archives = _materialize_bffs(inputs, stack)
        selected: list[Path] = []
        skipped: list[dict[str, str]] = []
        for path in archives:
            if _has_base_physics(path):
                selected.append(path)
            else:
                skipped.append({
                    "archive": path.name,
                    "reason": "no-base-physics-cdf-edf",
                })

        output_root = Path(
            stack.enter_context(
                tempfile.TemporaryDirectory(prefix="shift-physics-profile-")
            )
        )
        reports: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []

        for index, path in enumerate(sorted(selected, key=lambda p: p.name.lower())):
            output = output_root / f"{index:03d}_{path.stem}"
            try:
                report = extract_bundle(
                    path,
                    output,
                    strict=strict,
                )
            except Exception as exc:
                failures.append({
                    "archive": path.name,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                continue

            profile = report.get("profile") or {}
            summary = profile.get("summary") or {}
            reports.append({
                "archive": path.name,
                "status": report.get("status"),
                "ready": report.get("ready"),
                "entry_hashes": {
                    kind: {
                        "archive_path": info.get("archive_path"),
                        "raw_sha256": info.get("raw_sha256"),
                        "decoded_sha256": info.get("decoded_sha256"),
                    }
                    for kind, info in (report.get("entries") or {}).items()
                },
                "summary": {
                    "cdf_sections": summary.get("cdf_sections"),
                    "edf_entries": summary.get("edf_entries"),
                    "edf_rpm_torque_points": summary.get(
                        "edf_rpm_torque_points"
                    ),
                    "gdf_gear_ratio_count": summary.get(
                        "gdf_gear_ratio_count"
                    ),
                    "sdf_bodies": summary.get("sdf_bodies"),
                    "sdf_constraint_count": summary.get(
                        "sdf_constraint_count"
                    ),
                    "sdf_solver_scalar_count": summary.get(
                        "sdf_solver_scalar_count"
                    ),
                    "sdf_runtime_probe_ready": summary.get(
                        "sdf_runtime_probe_ready"
                    ),
                },
            })

    ready_count = sum(bool(report.get("ready")) for report in reports)
    return {
        "format": "SHIFT.VehiclePhysicsCorpusProfile/1",
        "version": 1,
        "strict": bool(strict),
        "input_count": len(list(inputs)) if not isinstance(inputs, (list, tuple)) else len(inputs),
        "selected_archive_count": len(selected),
        "decoded_archive_count": len(reports),
        "skipped": skipped,
        "failures": failures,
        "summary": {
            "ready_archives": ready_count,
            "warning_archives": len(reports) - ready_count,
            "failure_archives": len(failures),
            "archive_status_counts": dict(
                Counter(
                    str(report.get("status"))
                    for report in reports
                )
            ),
        },
        "archives": reports,
        "ready": bool(selected) and not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    report = profile_vehicle_physics_corpus(
        args.inputs,
        strict=args.strict,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
