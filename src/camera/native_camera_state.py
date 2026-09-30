"""Bridge evidence-backed CameraManager snapshots into native_runtime state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

SOURCE_FORMAT = "SHIFT.CameraStateSnapshotRuntime/1"
FORMAT = "SHIFT.NativeCameraState/1"

PROJECTION_DEFAULT_BITS = {
    "fov_bits": 0x3F490FDB,
    "aspect_ratio_bits": 0x3FAAAAAB,
    "near_z_bits": 0x3DCCCCCD,
    "far_z_bits": 0x443B8000,
}


def _int32(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if not -(1 << 31) <= result < (1 << 31):
        raise ValueError(f"{label} is outside signed 32-bit range")
    return result


def build_native_camera_state(
    snapshot_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Admit only the manager fields proven by FUN_0080e040."""
    if snapshot_report.get("format") != SOURCE_FORMAT:
        raise ValueError(
            "input must be SHIFT.CameraStateSnapshotRuntime/1"
        )

    snapshot = snapshot_report.get("snapshot")
    context = snapshot_report.get("source_context")
    blockers: list[str] = []
    if not isinstance(snapshot, Mapping):
        blockers.append("native-camera:snapshot-payload-missing")
        snapshot = {}
    if not isinstance(context, Mapping):
        blockers.append("native-camera:source-context-missing")
        context = {}

    values: dict[str, int | None] = {}
    fields = {
        "manager_mode": "word1_mode",
        "buffer_sub_index": "word2_buffer_sub_index",
        "camera_id": "word3_camera_id",
        "active_group": "word4_active_group",
        "group_restore_value": "word5_group_restore_value",
    }
    for output_name, source_name in fields.items():
        try:
            values[output_name] = _int32(
                snapshot.get(source_name),
                source_name,
            )
        except ValueError as exc:
            values[output_name] = None
            blockers.append(f"native-camera:{exc}")

    try:
        active_index = _int32(
            context.get("active_buffer_index"),
            "active_buffer_index",
        )
    except ValueError as exc:
        active_index = None
        blockers.append(f"native-camera:{exc}")
    if active_index not in (0, 1):
        blockers.append("native-camera:active-buffer-index-invalid")

    try:
        sub_flag = _int32(
            context.get("active_buffer_sub_flag"),
            "active_buffer_sub_flag",
        )
    except ValueError as exc:
        sub_flag = None
        blockers.append(f"native-camera:{exc}")
    if sub_flag is not None and not 0 <= sub_flag <= 0xFF:
        blockers.append("native-camera:active-buffer-sub-flag-out-of-range")

    # word0 is a retail runtime pointer/reference. Its presence is evidence, but
    # it has no portable identity in the native process and must not be copied.
    camera_source = snapshot.get("word0_camera_source")
    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "format": FORMAT,
        "version": 1,
        "status": "ready" if ready else "blocked",
        "ready": ready,
        "blocking_reasons": blockers,
        "active_buffer_index": active_index,
        "update_in_progress": False,
        "manager_mode": values["manager_mode"],
        "buffer_sub_index": values["buffer_sub_index"],
        "camera_id": values["camera_id"],
        "active_group": values["active_group"],
        "group_restore_value": values["group_restore_value"],
        "active_buffer_sub_flag": sub_flag,
        "projection_default_bits": dict(PROJECTION_DEFAULT_BITS),
        "source": {
            "format": snapshot_report.get("format"),
            "snapshot_function": "FUN_0080e040",
            "active_buffer_field": "+0x2560",
            "reentrancy_guard": "+0x269c",
            "opaque_camera_source_present": camera_source is not None,
        },
        "boundary": {
            "seeds_active_buffer_only": True,
            "inactive_buffer_state_inferred": False,
            "opaque_camera_source_admitted": False,
            "camera_behavior_inferred": False,
            "projection_defaults_source": (
                "CCameraView constructor defaults already used by native runtime"
            ),
            "double_buffer_swap_execution": "not-performed",
        },
    }


def build_native_camera_state_file(
    input_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(source, Mapping):
        raise ValueError("camera snapshot input must be a JSON object")
    report = build_native_camera_state(source)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args(argv)
    report = build_native_camera_state_file(args.input, args.output)
    print(json.dumps({
        "format": report["format"],
        "status": report["status"],
        "ready": report["ready"],
        "active_buffer_index": report["active_buffer_index"],
        "camera_id": report["camera_id"],
        "blocking_reasons": report["blocking_reasons"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
