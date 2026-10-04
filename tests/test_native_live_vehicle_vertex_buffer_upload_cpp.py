from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


def _has_vulkan_toolchain() -> bool:
    pkg_config = shutil.which("pkg-config")
    cxx = shutil.which(os.environ.get("CXX", "c++"))
    if pkg_config is None or cxx is None:
        return False
    return subprocess.run(
        [pkg_config, "--exists", "vulkan"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


def test_phase647_compiles_and_uploads_vehicle_vertices_to_real_vulkan_memory(
    tmp_path: Path,
) -> None:
    if not _has_vulkan_toolchain():
        pytest.skip("Vulkan development package is not installed")

    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "phase647_live_vehicle_vertex_upload"
    pkg_config = shutil.which("pkg-config")
    assert pkg_config is not None
    flags = subprocess.check_output(
        [pkg_config, "--cflags", "--libs", "vulkan"],
        text=True,
    ).split()

    subprocess.run(
        [
            os.environ.get("CXX", "c++"),
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-I",
            str(root / "native_runtime" / "include"),
            str(root / "native_runtime" / "src" / "vehicle_world_transform_transport.cpp"),
            str(root / "native_runtime" / "src" / "live_vehicle_vertex_buffer_upload.cpp"),
            str(root / "native_runtime" / "tests" / "live_vehicle_vertex_buffer_upload_check.cpp"),
            *flags,
            "-o",
            str(output),
        ],
        check=True,
        cwd=root,
    )

    env = dict(os.environ)
    # The dedicated workflow installs Mesa's software Vulkan ICD. Respect an
    # existing ICD override, otherwise allow the Vulkan loader to discover it.
    completed = subprocess.run(
        [str(output)],
        check=True,
        capture_output=True,
        text=True,
        cwd=root,
        env=env,
    )
    report = json.loads(completed.stdout.strip().splitlines()[-1])
    assert report == {
        "format": "SHIFT.LiveVehicleVertexBufferUpload/1",
        "ready": True,
        "vehicle_draw_count": 1,
        "track_buffers_untouched": True,
        "non_cumulative_reapply": True,
        "real_vulkan_memory_upload": True,
    }
