#!/usr/bin/env python3
"""Extract and verify FUN_007b2210 callsites from SHIFT.exe."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from specialized_provider_scalar_reset_callsite_extractor_runtime import (
    DEFAULT_FUNCTION_END,
    DEFAULT_FUNCTION_START,
    DEFAULT_TARGET,
    compare_extracted_callsites,
    extract_scalar_reset_callsites,
    validate_extracted_callsite_contract,
)
from specialized_provider_scalar_reset_callsite_runtime import CALLS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, help="retail SHIFT.exe")
    parser.add_argument(
        "--objdump",
        default="objdump",
        help="objdump executable (default: objdump)",
    )
    parser.add_argument(
        "--start",
        type=lambda value: int(value, 0),
        default=DEFAULT_FUNCTION_START,
    )
    parser.add_argument(
        "--stop",
        type=lambda value: int(value, 0),
        default=DEFAULT_FUNCTION_END,
    )
    parser.add_argument(
        "--target",
        type=lambda value: int(value, 0),
        default=DEFAULT_TARGET,
    )
    parser.add_argument("-o", "--output", type=Path)
    return parser


def _run_objdump(
    executable: Path,
    *,
    objdump: str,
    start: int,
    stop: int,
) -> str:
    if shutil.which(objdump) is None:
        raise RuntimeError(f"objdump not found: {objdump}")

    command = [
        objdump,
        "-d",
        "-M",
        "intel",
        f"--start-address=0x{start:08x}",
        f"--stop-address=0x{stop:08x}",
        str(executable),
    ]
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def expected_return_addresses() -> list[int]:
    return [
        int(entry["return_address"])
        for entry in CALLS
    ]


def analyze_executable(
    executable: Path,
    *,
    objdump: str = "objdump",
    start: int = DEFAULT_FUNCTION_START,
    stop: int = DEFAULT_FUNCTION_END,
    target: int = DEFAULT_TARGET,
) -> dict:
    disassembly = _run_objdump(
        executable,
        objdump=objdump,
        start=start,
        stop=stop,
    )
    extracted = extract_scalar_reset_callsites(
        disassembly,
        target_address=target,
        function_start=start,
        function_end=stop,
    )
    validation = validate_extracted_callsite_contract(
        extracted,
    )
    comparison = compare_extracted_callsites(
        extracted,
        expected_return_addresses(),
    )

    return {
        "format": "SHIFT.SpecializedProviderScalarResetCallsiteExtractionCLI/1",
        "version": 1,
        "executable": str(executable),
        "extracted": extracted,
        "validation": validation,
        "expected_comparison": comparison,
        "ready": bool(
            validation["ready"]
            and comparison["ready"]
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = analyze_executable(
        args.executable,
        objdump=args.objdump,
        start=args.start,
        stop=args.stop,
        target=args.target,
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

    print(
        json.dumps(
            {
                "format": report["format"],
                "ready": report["ready"],
                "call_count": report["extracted"]["call_count"],
                "return_addresses": report["extracted"]["return_addresses"],
                "validation_errors": report["validation"]["errors"],
                "comparison_ready": report["expected_comparison"]["ready"],
                "comparison_mismatch_count": report["expected_comparison"][
                    "mismatch_count"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
