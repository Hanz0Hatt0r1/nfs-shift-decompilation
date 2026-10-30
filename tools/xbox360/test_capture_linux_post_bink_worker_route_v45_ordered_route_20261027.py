#!/usr/bin/env python3
"""Regression checks for safe cleanup of ReXGlue shared-memory backing files."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "capture_linux_post_bink_worker_route_v45_ordered_route_20261027.py"
)
SPEC = importlib.util.spec_from_file_location("capture_route", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        shared = root / "shm"
        proc = root / "proc"
        shared.mkdir()
        held = shared / "xenia_memory_123"
        old = shared / "xenia_memory_456"
        held.write_bytes(b"held")
        old.write_bytes(b"preexisting")
        fd_dir = proc / "4321" / "fd"
        fd_dir.mkdir(parents=True)
        fd_link = fd_dir / "7"
        fd_link.symlink_to(held)

        first = MODULE.cleanup_orphaned_xenia_memory(
            {old.name}, shared_dir=shared, proc_root=proc
        )
        assert first == {"removed": [], "retained_open_or_unlink_failed": [held.name]}
        assert held.exists() and old.exists()

        fd_link.unlink()
        second = MODULE.cleanup_orphaned_xenia_memory(
            {old.name}, shared_dir=shared, proc_root=proc
        )
        assert second == {"removed": [held.name], "retained_open_or_unlink_failed": []}
        assert not held.exists() and old.exists()

    print("shared-memory cleanup retains live mappings and removes them after the holder exits")


if __name__ == "__main__":
    main()
