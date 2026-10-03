from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def test_phase646_native_transport_compiles_and_executes(tmp_path):
    compiler = shutil.which("c++")
    assert compiler is not None, "C++ compiler is required by native runtime CI"
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "phase646_transport_check"
    subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Wpedantic",
            "-I",
            str(root / "native_runtime" / "include"),
            str(root / "native_runtime" / "src" / "vehicle_world_transform_transport.cpp"),
            str(root / "native_runtime" / "tests" / "vehicle_world_transform_transport_check.cpp"),
            "-o",
            str(output),
        ],
        check=True,
        cwd=root,
    )
    result = subprocess.run(
        [str(output)],
        check=True,
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert '"format":"SHIFT.NativeVehicleWorldTransformTransportCheck/1"' in result.stdout
    assert '"non_cumulative_reapply":true' in result.stdout
