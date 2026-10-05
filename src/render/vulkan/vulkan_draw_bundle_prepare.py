"""Prepare one neutral SHIFT.VulkanDrawBundle/1 for native scene scheduling."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from vulkan_bundle_interface_gate import validate_vulkan_bundle_interface
from vulkan_bundle_spirv import compile_vulkan_bundle

FORMAT = "SHIFT.VulkanDrawBundlePrepare/1"
BUNDLE_FORMAT = "SHIFT.VulkanDrawBundle/1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_relative(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def _valid_sha256(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return text


def _artifact_pair(
    root: Path,
    *,
    label: str,
    path_value: Any,
    sha_value: Any,
) -> tuple[dict[str, Any] | None, list[str]]:
    relative = str(path_value or "").strip()
    blockers: list[str] = []
    if not _safe_relative(relative):
        return None, [f"vulkan-draw-prepare:artifact:{label}:path-unsafe"]
    expected = _valid_sha256(sha_value)
    if expected is None:
        return None, [f"vulkan-draw-prepare:artifact:{label}:sha256-invalid"]
    path = root / relative
    if not path.is_file():
        return None, [f"vulkan-draw-prepare:artifact:{label}:missing"]
    try:
        actual = _sha256(path)
    except OSError as error:
        blockers.append(
            f"vulkan-draw-prepare:artifact:{label}:read-failed:"
            + type(error).__name__
        )
        return None, blockers
    if actual != expected:
        blockers.append(
            f"vulkan-draw-prepare:artifact:{label}:sha256-mismatch"
        )
    return {
        "label": label,
        "path": relative,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "sha256_match": actual == expected,
    }, blockers


def _manifest_artifact_integrity(
    root: Path,
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping):
        return {
            "ready": False,
            "verified_count": 0,
            "artifacts": [],
        }, ["vulkan-draw-prepare:artifact-manifest-invalid"]

    blockers: list[str] = []
    verified: list[dict[str, Any]] = []

    def verify(
        label: str,
        row: Mapping[str, Any],
        *,
        path_key: str = "path",
        sha_key: str = "sha256",
    ) -> None:
        has_path = row.get(path_key) not in {None, ""}
        has_sha = row.get(sha_key) not in {None, ""}
        if not has_path and not has_sha:
            return
        if not has_path or not has_sha:
            blockers.append(
                f"vulkan-draw-prepare:artifact:{label}:identity-incomplete"
            )
            return
        report, reasons = _artifact_pair(
            root,
            label=label,
            path_value=row.get(path_key),
            sha_value=row.get(sha_key),
        )
        blockers.extend(reasons)
        if report is not None:
            verified.append(report)

    for name, raw in artifacts.items():
        label = str(name)
        if raw is None:
            continue
        if isinstance(raw, Mapping):
            verify(label, raw)
            if (
                "metadata_path" in raw
                or "metadata_sha256" in raw
            ):
                verify(
                    label + ".metadata",
                    raw,
                    path_key="metadata_path",
                    sha_key="metadata_sha256",
                )
            continue
        if isinstance(raw, list):
            for index, item in enumerate(raw):
                item_label = f"{label}[{index}]"
                if not isinstance(item, Mapping):
                    blockers.append(
                        f"vulkan-draw-prepare:artifact:{item_label}:invalid-row"
                    )
                    continue
                verify(item_label, item)
            continue
        blockers.append(
            f"vulkan-draw-prepare:artifact:{label}:invalid-row"
        )

    blockers = list(dict.fromkeys(blockers))
    return {
        "ready": not blockers,
        "verified_count": len(verified),
        "artifacts": verified,
    }, blockers


def _ready_gate(root: Path, name: str, format_name: str) -> tuple[dict[str, Any] | None, list[str]]:
    path = root / name
    if not path.is_file():
        return None, [f"vulkan-draw-prepare:{name}:missing"]
    try:
        value = _load(path)
    except (OSError, ValueError, TypeError) as error:
        return None, [
            f"vulkan-draw-prepare:{name}:invalid:{type(error).__name__}"
        ]
    blockers: list[str] = []
    if value.get("format") != format_name:
        blockers.append(f"vulkan-draw-prepare:{name}:invalid-format")
    if value.get("ready") is not True:
        blockers.extend(
            f"vulkan-draw-prepare:{name}:{reason}"
            for reason in value.get("blocking_reasons") or ["not-ready"]
        )
    return value, list(dict.fromkeys(blockers))


def prepare_vulkan_draw_bundle(
    bundle_dir: str | Path,
    *,
    validator: str | None = None,
    output: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(bundle_dir)
    manifest_path = root / "bundle_manifest.json"
    output_path = (
        Path(output)
        if output is not None
        else root / "vulkan_draw_prepare.json"
    )

    blockers: list[str] = []
    manifest: dict[str, Any] | None = None
    if not manifest_path.is_file():
        blockers.append("vulkan-draw-prepare:manifest-missing")
    else:
        try:
            manifest = _load(manifest_path)
        except (OSError, ValueError, TypeError) as error:
            blockers.append(
                "vulkan-draw-prepare:manifest-invalid:"
                + type(error).__name__
            )

    if manifest is not None:
        if manifest.get("format") != BUNDLE_FORMAT:
            blockers.append("vulkan-draw-prepare:invalid-bundle-format")
        if manifest.get("ready") is not True:
            blockers.extend(
                f"vulkan-draw-prepare:bundle:{reason}"
                for reason in manifest.get("blocking_reasons")
                or ["not-ready"]
            )

    artifact_integrity: dict[str, Any] = {
        "ready": False,
        "verified_count": 0,
        "artifacts": [],
    }
    if manifest is not None:
        artifact_integrity, artifact_blockers = _manifest_artifact_integrity(
            root,
            manifest,
        )
        blockers.extend(artifact_blockers)

    native_gate, native_blockers = _ready_gate(
        root,
        "native_submission_gate.json",
        "SHIFT.NativeSubmissionGate/1",
    )
    provenance_gate, provenance_blockers = _ready_gate(
        root,
        "runtime_provenance_gate.json",
        "SHIFT.VulkanDrawRuntimeProvenanceGate/1",
    )
    blockers.extend(native_blockers)
    blockers.extend(provenance_blockers)

    transform_report: dict[str, Any] | None = None
    if manifest is not None:
        scene_transform = manifest.get("scene_transform") or {}
        world_matrix = scene_transform.get("world_matrix")
        packet = scene_transform.get("packet")
        if world_matrix is not None:
            if not isinstance(packet, dict):
                blockers.append(
                    "vulkan-draw-prepare:world-transform-packet-missing"
                )
            else:
                if packet.get("format") != "SHIFT.VulkanWorldTransformPacket/1":
                    blockers.append(
                        "vulkan-draw-prepare:world-transform-format-invalid"
                    )
                relative = str(packet.get("path") or "")
                packet_path = root / relative
                expected_sha = str(packet.get("sha256") or "").lower()
                if (
                    not relative
                    or Path(relative).is_absolute()
                    or ".." in Path(relative).parts
                ):
                    blockers.append(
                        "vulkan-draw-prepare:world-transform-path-unsafe"
                    )
                elif not packet_path.is_file():
                    blockers.append(
                        "vulkan-draw-prepare:world-transform-packet-missing"
                    )
                else:
                    actual_sha = _sha256(packet_path)
                    if len(expected_sha) != 64 or actual_sha != expected_sha:
                        blockers.append(
                            "vulkan-draw-prepare:world-transform-sha256-mismatch"
                        )
                    else:
                        transform_report = {
                            "format": packet.get("format"),
                            "path": relative,
                            "sha256": actual_sha,
                            "ready": True,
                            "execution_capability": (
                                "semantic-affine-native-material-path"
                            ),
                        }

    compile_report: dict[str, Any] | None = None
    interface_report: dict[str, Any] | None = None
    if not blockers:
        try:
            compile_report = compile_vulkan_bundle(
                root,
                validator=validator,
            )
        except (OSError, ValueError, TypeError) as error:
            blockers.append(
                "vulkan-draw-prepare:spirv:"
                + type(error).__name__
            )
        else:
            spirv_path = root / "spirv_report.json"
            spirv_path.write_text(
                json.dumps(
                    compile_report,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            if compile_report.get("ready") is not True:
                blockers.extend(
                    str(reason)
                    for reason in compile_report.get("blocking_reasons")
                    or ["vulkan-draw-prepare:spirv-not-ready"]
                )
            else:
                interface_report = validate_vulkan_bundle_interface(
                    root,
                    compile_report,
                )
                interface_path = root / "vulkan_interface.json"
                interface_path.write_text(
                    json.dumps(
                        interface_report,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                if interface_report.get("ready") is not True:
                    blockers.extend(
                        str(reason)
                        for reason in interface_report.get(
                            "blocking_reasons"
                        )
                        or ["vulkan-draw-prepare:interface-not-ready"]
                    )

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    artifacts: dict[str, Any] = {}
    for key, path in (
        ("manifest", manifest_path),
        ("native_submission_gate", root / "native_submission_gate.json"),
        ("runtime_provenance_gate", root / "runtime_provenance_gate.json"),
        ("spirv_report", root / "spirv_report.json"),
        ("interface_report", root / "vulkan_interface.json"),
    ):
        if path.is_file():
            artifacts[key] = {
                "path": str(path.relative_to(root)),
                "sha256": _sha256(path),
            }
    if transform_report is not None:
        artifacts["world_transform"] = transform_report

    result = {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "bundle_format": (
            manifest.get("format") if manifest is not None else None
        ),
        "source_manifest_sha256": (
            _sha256(manifest_path) if manifest_path.is_file() else None
        ),
        "manifest_artifact_integrity": artifact_integrity,
        "native_submission_gate_ready": (
            native_gate is not None and not native_blockers
        ),
        "runtime_provenance_gate_ready": (
            provenance_gate is not None and not provenance_blockers
        ),
        "world_transform": transform_report,
        "spirv": compile_report,
        "interface": interface_report,
        "artifacts": artifacts,
        "boundary": {
            "atomic_bundle_prepared": ready,
            "manifest_declared_artifacts_sha256_revalidated": (
                artifact_integrity.get("ready") is True
            ),
            "artifact_integrity_checked_before_compile": True,
            "world_transform_execution_supported": (
                transform_report is not None
                or (
                    manifest is not None
                    and (manifest.get("scene_transform") or {}).get(
                        "world_matrix"
                    )
                    is None
                )
            ),
            "executes_native_runtime": False,
            "assigns_retail_world_constant_register": False,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_dir")
    parser.add_argument("--validator")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = prepare_vulkan_draw_bundle(
        args.bundle_dir,
        validator=args.validator,
        output=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
