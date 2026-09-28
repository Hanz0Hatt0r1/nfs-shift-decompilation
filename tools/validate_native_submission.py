#!/usr/bin/env python3
"""Validate strict native-execution provenance for a RenderCommand/1 JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from render_submission_gate import validate_native_submission


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="SHIFT.RenderCommand/1 JSON")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    command = json.loads(args.input.read_text(encoding="utf-8"))
    result = validate_native_submission(command)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
