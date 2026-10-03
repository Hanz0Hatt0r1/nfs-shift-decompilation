from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "shift_resource_pipeline_cli",
    ROOT / "tools" / "shift_resource_pipeline.py",
)
assert SPEC is not None and SPEC.loader is not None
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def _args(tmp_path: Path, *, require: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        inputs=["Vehicles.zip", "Silverstone_Era3_.zip"],
        output=str(tmp_path / "pipeline"),
        track="Silverstone_Era3_GrandPrix",
        vehicle="BMW_M3_E36",
        scene_set="out/runtime-proven-scene",
        require_native_resource_handoff=require,
        decode_limit_per_archive=0,
    )


def test_all_automatically_builds_native_resource_handoff(monkeypatch, tmp_path):
    calls = {}

    def fake_run(inputs, output, *, track, vehicle, decode_limit_per_archive):
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        for name in (
            "resource_catalog.json",
            "scene_vehicle_bootstrap.json",
            "vehicle_physics_bundle_report.json",
        ):
            (out / name).write_text("{}\n", encoding="utf-8")
        calls["run"] = {
            "inputs": list(inputs),
            "track": track,
            "vehicle": vehicle,
            "limit": decode_limit_per_archive,
        }
        return {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "resource_bootstrap_ready": True,
            "native_runtime_ready": False,
            "artifacts": {"catalog": str(out / "resource_catalog.json")},
            "boundary": {"provenance_gate_bypass": False},
        }

    def fake_handoff(catalog, bootstrap, physics, output, *, scene_set_dir=None):
        calls["handoff"] = {
            "catalog": str(catalog),
            "bootstrap": str(bootstrap),
            "physics": str(physics),
            "output": str(output),
            "scene_set": scene_set_dir,
        }
        return {
            "format": "SHIFT.OfflineNativeResourceHandoff/1",
            "status": "ready",
            "ready": True,
            "resource_inputs_ready": True,
            "blocking_reasons": [],
            "artifacts": {
                "native_physics_manifest": {
                    "path": str(Path(output) / "native_physics_manifest.json"),
                    "sha256": "a" * 64,
                }
            },
        }

    monkeypatch.setattr(cli, "run_offline_pipeline", fake_run)
    monkeypatch.setattr(cli, "build_native_resource_handoff_files", fake_handoff)

    args = _args(tmp_path)
    assert cli.cmd_all(args) == 0
    assert calls["handoff"]["scene_set"] == "out/runtime-proven-scene"
    assert calls["handoff"]["catalog"].endswith("resource_catalog.json")
    assert calls["handoff"]["bootstrap"].endswith("scene_vehicle_bootstrap.json")
    assert calls["handoff"]["physics"].endswith("vehicle_physics_bundle_report.json")

    persisted = json.loads(
        (Path(args.output) / "pipeline_run.json").read_text(encoding="utf-8")
    )
    assert persisted["resource_bootstrap_ready"] is True
    assert persisted["native_resource_handoff_ready"] is True
    assert persisted["native_runtime_ready"] is False
    assert persisted["inputs"]["runtime_proven_scene_set"] == str(
        Path(args.scene_set).resolve()
    )
    assert persisted["boundary"]["native_resource_handoff_automated"] is True
    assert persisted["boundary"]["native_resource_handoff_is_runtime_execution"] is False
    assert persisted["boundary"]["runtime_proven_scene_set_recorded"] is True
    assert persisted["artifacts"]["native_handoff_native_physics_manifest"].endswith(
        "native_physics_manifest.json"
    )


def test_all_can_require_native_resource_handoff(monkeypatch, tmp_path):
    def fake_run(inputs, output, *, track, vehicle, decode_limit_per_archive):
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        return {
            "format": "SHIFT.OfflineResourcePipelineRun/1",
            "resource_bootstrap_ready": True,
            "native_runtime_ready": False,
            "artifacts": {},
            "boundary": {},
        }

    def blocked_handoff(*args, **kwargs):
        return {
            "format": "SHIFT.OfflineNativeResourceHandoff/1",
            "status": "blocked",
            "ready": False,
            "resource_inputs_ready": False,
            "blocking_reasons": ["scene:scene-set:runtime-proven-input-required"],
            "artifacts": {},
        }

    monkeypatch.setattr(cli, "run_offline_pipeline", fake_run)
    monkeypatch.setattr(cli, "build_native_resource_handoff_files", blocked_handoff)

    optional = _args(tmp_path / "optional", require=False)
    assert cli.cmd_all(optional) == 0

    required = _args(tmp_path / "required", require=True)
    assert cli.cmd_all(required) == 2
    persisted = json.loads(
        (Path(required.output) / "pipeline_run.json").read_text(encoding="utf-8")
    )
    assert persisted["native_resource_handoff_ready"] is False
    assert persisted["native_resource_handoff_blocking_reasons"] == [
        "scene:scene-set:runtime-proven-input-required"
    ]


def test_all_parser_exposes_scene_set_and_strict_handoff_flag():
    parser = cli.build_parser()
    args = parser.parse_args([
        "all",
        "Vehicles.zip",
        "Silverstone_Era3_.zip",
        "-o",
        "out/pipeline",
        "--track",
        "Silverstone_Era3_GrandPrix",
        "--vehicle",
        "BMW_M3_E36",
        "--scene-set",
        "out/native-scene-vulkan",
        "--require-native-resource-handoff",
    ])
    assert args.scene_set == "out/native-scene-vulkan"
    assert args.require_native_resource_handoff is True
