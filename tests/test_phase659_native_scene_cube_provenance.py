from __future__ import annotations

import struct
from pathlib import Path

from native_scene_vulkan_set import build_native_scene_vulkan_set
from test_native_scene_vulkan_set import _scene_and_bridge


def _dds_header(width: int = 4, height: int = 4, *, caps2: int = 0) -> bytes:
    fourcc = b"DXT1"
    values = (
        124, 0, height, width, 0, 0, 1,
        *([0] * 11),
        32, 0x4, struct.unpack("<I", fourcc)[0], 0,
        0, 0, 0, 0,
        0x1000, caps2, 0, 0, 0,
    )
    return b"DDS " + struct.pack("<31I", *values)


def _write_valid_cube(path: Path) -> None:
    all_faces = 0x400 | 0x800 | 0x1000 | 0x2000 | 0x4000 | 0x8000
    dxt1_block = struct.pack("<HHI", 0xF800, 0x07E0, 0)
    path.write_bytes(
        _dds_header(caps2=0x200 | all_faces)
        + b"".join(dxt1_block for _ in range(6))
    )


def test_phase659_global_cube_dds_cannot_satisfy_scene_bound_s3(tmp_path: Path):
    root, scene, bridge = _scene_and_bridge(
        tmp_path,
        external_cube=True,
    )
    cube = tmp_path / "legacy-environment.dds"
    _write_valid_cube(cube)

    report = build_native_scene_vulkan_set(
        scene,
        bridge,
        root,
        tmp_path / "vulkan-set",
        environment_cube_dds=cube,
    )

    assert report["ready"] is False
    assert (
        "environment-cube:global-dds-not-runtime-proven-for-scene"
        in report["blocking_reasons"]
    )
    assert report["source"]["external_sampler_cube_snapshot_count"] == 0
    assert report["draws"][0]["external_cube_source"] is None
    assert (
        "draw-0:external-sampler:runtime-resource-unresolved:s3:samplerCube"
        in report["native_scene_submission"]["blocking_reasons"]
    )
    assert (
        report["boundary"][
            "scene_external_samplercube_requires_runtime_snapshot"
        ]
        is True
    )
    assert (
        report["boundary"][
            "global_environment_cube_dds_is_scene_runtime_authority"
        ]
        is False
    )
