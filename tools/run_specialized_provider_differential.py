#!/usr/bin/env python3
"""Run the experimental specialized-provider numeric solver against a capture."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sdf_solver_capture_runtime import normalize_solver_capture
from specialized_provider_capture_differential_runtime import (
    run_capture_differential,
)
from specialized_provider_source_pattern_executor_adapter_runtime import (
    extract_source_factor_edges,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pre",
        type=Path,
        required=True,
        help="normalized pre_solve_XXXXXX.json",
    )
    parser.add_argument(
        "--post",
        type=Path,
        help="optional post_solve_XXXXXX.json",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="optional local retail SHIFT.exe.c for provider factor topology",
    )
    parser.add_argument(
        "--provider",
        type=int,
        choices=(0, 1),
        help="specialized provider id; required with --source",
    )
    parser.add_argument("--abs-tol", type=float, default=0.0)
    parser.add_argument("--rel-tol", type=float, default=0.0)
    parser.add_argument("-o", "--output", type=Path)
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.source is not None and args.provider is None:
        raise ValueError("--provider is required when using --source")

    pre = _load_json(args.pre)
    normalize_solver_capture(pre)

    post = _load_json(args.post) if args.post is not None else None
    source_pattern = None
    factor_edges = None

    if args.source is not None:
        source_pattern = extract_source_factor_edges(
            args.source.read_text(encoding="utf-8"),
            provider_id=args.provider,
        )
        if not source_pattern["ready"]:
            report = {
                "format": "SHIFT.SpecializedProviderCaptureDifferentialCLI/1",
                "version": 1,
                "status": "blocked",
                "ready": False,
                "mode": "source-pattern-guided",
                "errors": [
                    {
                        "kind": "source-pattern",
                        "message": "; ".join(
                            str(error)
                            for error in source_pattern["errors"]
                        ),
                    }
                ],
            }
        else:
            factor_edges = {
                (
                    int(item["pivot_index"]),
                    int(item["column"]),
                )
                for item in source_pattern["edges"]
            }
            report = run_capture_differential(
                pre,
                expected_post_solve=post,
                factor_edges=factor_edges,
                abs_tol=args.abs_tol,
                rel_tol=args.rel_tol,
            )
            report["source_pattern"] = {
                "provider_id": source_pattern["provider_id"],
                "scalar_count": source_pattern["scalar_count"],
                "edge_count": source_pattern["edge_count"],
                "ready": source_pattern["ready"],
            }
    else:
        report = run_capture_differential(
            pre,
            expected_post_solve=post,
            abs_tol=args.abs_tol,
            rel_tol=args.rel_tol,
        )

    payload = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        default=str,
    ) + "
"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report["status"],
                "ready": report["ready"],
                "mode": report.get("mode"),
                "scalar_count": report.get("scalar_count"),
                "errors": report.get("errors", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
