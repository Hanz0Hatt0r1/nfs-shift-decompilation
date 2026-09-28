"""Pytest bootstrap for the src-based repository layout.

The project intentionally keeps historical bare-module imports while source
modules are grouped by subsystem under src/.  Test collection must therefore
expose src and its subsystem directories before importing legacy test modules.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if SRC.is_dir():
    PATHS = [SRC]
    PATHS.extend(
        sorted(
            (path for path in SRC.rglob("*") if path.is_dir()),
            key=lambda path: (len(path.parts), str(path)),
        )
    )
    for path in reversed(PATHS):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
