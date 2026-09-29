"""Prepare every draw in SHIFT.BMWVulkanBundleSet/1 for native execution."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from vulkan_bundle_run import run_bmw_vulkan_bundle

FORMAT = "SHIFT.BMWVulkanBundleSetPrepare/1"
SET_FORMAT = "SHIFT.BMWVulkanBundleSet/1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": 1,
        "status": "blocked",
        "ready": False,
        "blocking_reasons": [reason],
        "draw_count": 0,
        "draws": [],
    }


def _safe_relative_bundle_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def prepare_bmw_vulkan_bundle_set(
    bundle_set_dir: str | Path,
    *,
    validator: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(bundle_set_dir)
    manifest_path = root / "bundle_set_manifest.json"
    paths_path = root / "bundle_set.paths"
    output_path = Path(output) if output is not None else root / "bundle_set_prepare.json"

    if not manifest_path.is_file():
        result = _blocked("bundle-set-prepare:manifest-missing")
    elif not paths_path.is_file():
        result = _blocked("bundle-set-prepare:draw-order-missing")
    else:
        try:
            manifest = _load(manifest_path)
        except (OSError, ValueError, TypeError) as error:
            result = _blocked(
                f"bundle-set-prepare:manifest-invalid:{type(error).__name__}"
            )
        else:
            blockers: list[str] = []
            if manifest.get("format") != SET_FORMAT:
                blockers.append("bundle-set-prepare:invalid-format")
            if manifest.get("ready") is not True:
                blockers.extend(
                    str(reason)
                    for reason in manifest.get("blocking_reasons")
                    or ["bundle-set-prepare:set-not-ready"]
                )

            draw_rows = manifest.get("draws") or []
            if not isinstance(draw_rows, list) or not draw_rows:
                blockers.append("bundle-set-prepare:draws-missing")
                draw_rows = []

            paths = [
                line.strip()
                for line in paths_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if len(paths) != len(draw_rows):
                blockers.append("bundle-set-prepare:draw-order-count-mismatch")

            for index, relative in enumerate(paths):
                if not _safe_relative_bundle_path(relative):
                    blockers.append(
                        f"bundle-set-prepare:unsafe-bundle-path:{index}"
                    )
                    continue
                if index < len(draw_rows):
                    expected = str(draw_rows[index].get("bundle_path") or "")
                    if relative != expected:
                        blockers.append(
                            f"bundle-set-prepare:draw-order-path-mismatch:{index}"
                        )

            prepared_draws: list[dict[str, Any]] = []
            if not blockers:
                for index, relative in enumerate(paths):
                    child = root / relative
                    child_result = run_bmw_vulkan_bundle(
                        child,
                        validator=validator,
                        prepare_only=True,
                    )
                    child_blockers = [
                        str(reason)
                        for reason in child_result.get("blocking_reasons") or []
                    ]
                    child_ready = (
                        child_result.get("ready") is True
                        and child_result.get("status") == "ready"
                    )
                    spirv = child / "spirv_report.json"
                    interface = child / "vulkan_interface.json"
                    if child_ready and not spirv.is_file():
                        child_ready = False
                        child_blockers.append(
                            "bundle-set-prepare:spirv-report-missing"
                        )
                    if child_ready and not interface.is_file():
                        child_ready = False
                        child_blockers.append(
                            "bundle-set-prepare:interface-report-missing"
                        )
                    if not child_ready:
                        if child_blockers:
                            blockers.extend(
                                f"bundle-set-prepare:draw-{index}:{reason}"
                                for reason in child_blockers
                            )
                        else:
                            blockers.append(
                                f"bundle-set-prepare:draw-{index}:not-ready"
                            )

                    source_row = draw_rows[index]
                    prepared_draws.append({
                        "draw_order": index,
                        "source_submesh_index": source_row.get(
                            "source_submesh_index"
                        ),
                        "bundle_path": relative,
                        "ready": child_ready,
                        "status": child_result.get("status"),
                        "blocking_reasons": child_blockers,
                        "spirv_report": (
                            {
                                "path": str(spirv.relative_to(root)),
                                "sha256": _sha256(spirv),
                            }
                            if spirv.is_file() else None
                        ),
                        "interface_report": (
                            {
                                "path": str(interface.relative_to(root)),
                                "sha256": _sha256(interface),
                            }
                            if interface.is_file() else None
                        ),
                    })

            result = {
                "format": FORMAT,
                "version": 1,
                "status": "ready" if not blockers else "blocked",
                "ready": not blockers,
                "blocking_reasons": list(dict.fromkeys(blockers)),
                "source": {
                    "manifest_path": str(manifest_path),
                    "manifest_sha256": _sha256(manifest_path),
                    "draw_order_path": str(paths_path),
                    "draw_order_sha256": _sha256(paths_path),
                },
                "draw_count": len(prepared_draws),
                "draws": prepared_draws,
            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile and validate every draw in SHIFT.BMWVulkanBundleSet/1"
    )
    parser.add_argument("bundle_set_dir")
    parser.add_argument("--validator")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = prepare_bmw_vulkan_bundle_set(
        args.bundle_set_dir,
        validator=args.validator,
        output=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
