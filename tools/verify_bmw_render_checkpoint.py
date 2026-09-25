#!/usr/bin/env python3
"""Verify a repository-visible BMW render checkpoint against its scene manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


FORMAT = "SHIFT.BMWRenderCheckpointVerifier/1"


def _png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("screenshot is not a PNG")
    if data[12:16] != b"IHDR" or len(data) < 24:
        raise ValueError("PNG is missing a valid IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid PNG dimensions: {width}x{height}")
    return width, height


def verify(scene_path: str | Path, *, repo_root: str | Path | None = None) -> dict[str, object]:
    scene_file = Path(scene_path).resolve()
    root = Path(repo_root).resolve() if repo_root is not None else scene_file.parents[2]
    scene = json.loads(scene_file.read_text(encoding="utf-8"))

    screenshot = root / str(scene["screenshot"]["path"])
    expected_sha = str(scene["screenshot"]["sha256"])
    expected_width = int(scene["screenshot"]["width"])
    expected_height = int(scene["screenshot"]["height"])

    data = screenshot.read_bytes()
    width, height = _png_size(data)
    actual_sha = hashlib.sha256(data).hexdigest()

    checks = {
        "format": scene.get("format") == "SHIFT.BMWM3RenderDemoScene/1",
        "ready": scene.get("ready") is True,
        "target_resource": scene.get("source", {}).get("resource")
        == "vehicles/bmw_m3_e36/bmw_m3_e36_kit00_body_loda.meb",
        "screenshot_exists": screenshot.exists(),
        "dimensions": (width, height) == (expected_width, expected_height),
        "sha256": actual_sha == expected_sha,
    }

    failed = [name for name, ok in checks.items() if not ok]
    result = {
        "format": FORMAT,
        "status": "verified" if not failed else "blocked",
        "ready": not failed,
        "scene": str(scene_file.relative_to(root)),
        "screenshot": str(screenshot.relative_to(root)),
        "checks": checks,
        "observed": {
            "width": width,
            "height": height,
            "sha256": actual_sha,
        },
        "expected": {
            "width": expected_width,
            "height": expected_height,
            "sha256": expected_sha,
        },
        "blocking_reasons": failed,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scene",
        type=Path,
        help="BMW render demo scene manifest",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="repository root; defaults to the project root inferred from the scene path",
    )
    args = parser.parse_args()

    result = verify(args.scene, repo_root=args.repo_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
