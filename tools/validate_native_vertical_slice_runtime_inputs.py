#!/usr/bin/env python3
"""Compatibility entrypoint for launcher-equivalent runtime input validation."""
from __future__ import annotations

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

from runtime_input_validation import validate_explicit_runtime_inputs

__all__ = ["validate_explicit_runtime_inputs"]
