#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

MODULE_PATH = Path(__file__).with_name("capture_bmw_body0.py")
spec = importlib.util.spec_from_file_location("capture_bmw_body0", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_parse_regions() -> None:
    regions = module._parse_regions(["0x401000:64:text", "0x10:0x20"])
    assert regions == [(0x401000, 64, "text"), (0x10, 0x20, "0x10")]


def test_maps_digest_current_process() -> None:
    import os

    digest, lines = module._maps_digest(os.getpid())
    assert len(digest) == 64
    assert lines


def test_write_json() -> None:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "x.json"
        module._write_json(path, {"b": 2, "a": 1})
        text = path.read_text(encoding="utf-8")
        assert '"a": 1' in text
        assert text.endswith("\n")


if __name__ == "__main__":
    test_parse_regions()
    test_maps_digest_current_process()
    test_write_json()
    print("capture_bmw_body0 tests: PASS")
