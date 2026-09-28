#!/usr/bin/env python3
"""Verify and analyze a specialized-provider runtime capture session."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from specialized_provider_capture_session_runtime import (
    build_provider_session_contract,
)
from specialized_provider_source_capture_crosscheck_runtime import (
    build_source_capture_crosscheck,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pre",
        type=Path,
        required=True,
        help="provider_pre_<id>_<hit>.json",
    )
    parser.add_argument(
        "--post",
        type=Path,
        help="optional provider_post_<id>_<hit>.json",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="optional local retail SHIFT.exe.c",
    )
    parser.add_argument(
        "--provider",
        type=int,
        choices=(0, 1),
        help="expected provider id",
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

    pre = _load_json(args.pre)
    post = _load_json(args.post) if args.post else None

    actual_provider = int(pre.get("provider_id", -1))
    if args.provider is not None and actual_provider != args.provider:
        report = {
            "format": "SHIFT.SpecializedProviderCaptureCLI/1",
            "version": 1,
            "status": "blocked",
            "ready": False,
            "provider_id": actual_provider,
            "errors": [
                {
                    "kind": "provider-id-mismatch",
                    "expected": args.provider,
                    "observed": actual_provider,
                }
            ],
        }
    else:
        source_text = (
            args.source.read_text(encoding="utf-8")
            if args.source is not None
            else None
        )
        report = build_provider_session_contract(
            pre,
            post_solve=post,
            reset_source=source_text,
            abs_tol=args.abs_tol,
            rel_tol=args.rel_tol,
        )

        if (
            source_text is not None
            and post is not None
            and report.get("ready")
        ):
            source_pattern = __import__(
                "specialized_provider_source_pattern_executor_adapter_runtime",
                fromlist=["extract_source_factor_edges"],
            ).extract_source_factor_edges(
                source_text,
                provider_id=actual_provider,
            )
            crosscheck = build_source_capture_crosscheck(
                source_text,
                pre,
                post,
                provider_id=actual_provider,
                abs_tol=args.abs_tol,
                rel_tol=args.rel_tol,
            )
            report["source_factor_crosscheck"] = {
                "provider_id": source_pattern["provider_id"],
                "edge_count": source_pattern["edge_count"],
                "ready": crosscheck.get("ready"),
                "summary": {
                    "overlap_count": crosscheck.get("overlap_count", 0),
                    "factor_address_not_observed_changed_count": crosscheck.get(
                        "factor_address_not_observed_changed_count",
                        0,
                    ),
                    "capture_workspace_change_not_factor_count": crosscheck.get(
                        "capture_workspace_change_not_factor_count",
                        0,
                    ),
                },
                "errors": crosscheck.get("errors", []),
            }
            if not crosscheck.get("ready"):
                report["ready"] = False
                report.setdefault("errors", []).append(
                    "source-factor-crosscheck-not-ready"
                )

    payload = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    summary = report.get("summary") or {}
    print(
        json.dumps(
            {
                "format": report["format"],
                "status": report.get("status"),
                "ready": report.get("ready"),
                "provider_id": report.get("provider_id"),
                "scalar_count": report.get("scalar_count"),
                "workspace_changes": summary.get("workspace_changes"),
                "output_changes": summary.get("output_changes"),
                "reset_zero_slot_deviations": summary.get(
                    "reset_zero_slot_deviations"
                ),
                "outside_reset_domain_nonzero": summary.get(
                    "outside_reset_domain_nonzero"
                ),
                "source_factor_crosscheck": report.get(
                    "source_factor_crosscheck"
                ),
                "errors": report.get("errors", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report.get("ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
