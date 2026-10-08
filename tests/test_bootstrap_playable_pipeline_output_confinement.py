from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bootstrap_playable_pipeline_output_confinement",
    ROOT / "tools" / "bootstrap_playable_pipeline_slice.py",
)
assert SPEC is not None and SPEC.loader is not None
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


def _argv(workspace: Path, output: Path) -> list[str]:
    return [
        "Vehicles.zip",
        "Silverstone.zip",
        "-o",
        str(output),
        "--track",
        "Silverstone_Era3_GrandPrix",
        "--vehicle",
        "BMW_M3_E36",
        "--workspace-root",
        str(workspace),
        "--resource-pipeline",
        "out/offline-pipeline",
        "--camera-state",
        "runtime/camera.json",
        "--solver-frame",
        "runtime/solver.sbfr",
        "--generated-body-constraint-frame",
        "runtime/generated.gbcf",
        "--constraint-sample-relation-frame",
        "runtime/relations.csrf",
        "--constraint-relation-reset-frame",
        "runtime/reset.crrf",
        "--post-solve-projection",
        "runtime/post.sbps",
        "--keyboard",
        "--frames",
        "3",
    ]


def test_output_outside_workspace_fails_before_pipeline_or_filesystem_side_effects(
    monkeypatch,
    tmp_path,
    capsys,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside-output"

    def unexpected(*args, **kwargs):
        raise AssertionError("resource pipeline must not be touched for invalid output")

    monkeypatch.setattr(CLI.native, "_resolve_resource_pipeline_inputs", unexpected)

    assert CLI.main(_argv(workspace, outside)) == 2
    assert not outside.exists()
    assert "--output must be inside --workspace-root" in capsys.readouterr().err


def test_missing_workspace_fails_before_output_creation(monkeypatch, tmp_path, capsys):
    workspace = tmp_path / "missing-workspace"
    output = workspace / "out"

    def unexpected(*args, **kwargs):
        raise AssertionError("resource pipeline must not be touched for missing workspace")

    monkeypatch.setattr(CLI.native, "_resolve_resource_pipeline_inputs", unexpected)

    assert CLI.main(_argv(workspace, output)) == 2
    assert not output.exists()
    assert "--workspace-root directory not found" in capsys.readouterr().err
