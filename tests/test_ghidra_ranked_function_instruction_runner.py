from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ghidra" / "run_ranked_function_instructions.py"
SPEC = importlib.util.spec_from_file_location("run_ranked_function_instructions", TOOL)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def _write(path: Path, payload):
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return path


def _rank(
    path: Path,
    selected,
    *,
    ready=True,
    md5=None,
    declared_limit=None,
    artifact_format=None,
):
    ranking = {"selected_instruction_export_functions": selected}
    if declared_limit is not None:
        ranking["selected_instruction_export_limit"] = declared_limit
    return _write(
        path,
        {
            "format": artifact_format or m.RANK_FORMAT,
            "ready": ready,
            "retail": {"program": m.PROGRAM, "md5": md5 or m.PE_MD5},
            "ranking": ranking,
        },
    )


def _root_pose(path: Path, selected, *, ready=True, md5=None, worklist_format=None):
    return _write(
        path,
        {
            "format": m.ROOT_POSE_FORMAT,
            "ready": ready,
            "retail": {
                "program_name": m.PROGRAM,
                "executable_md5": md5 or m.PE_MD5,
            },
            "targeted_instruction_worklist": {
                "format": worklist_format or m.INSTRUCTION_FORMAT,
                "functions": selected,
            },
        },
    )


def test_builds_exact_runner_command_from_rank_selected_worklist(tmp_path):
    artifact = _rank(
        tmp_path / "rank.json",
        ["FUN_00410000", "0x00420000", "00430000"],
        declared_limit=24,
    )
    runner = tmp_path / "runner.sh"
    command, selected = m.build_command(
        artifact,
        Path("/home/pes/ghidra_projects/shift"),
        "shift",
        Path("out/selected.jsonl"),
        runner=runner,
    )
    assert selected == ["0x00410000", "0x00420000", "0x00430000"]
    assert command == [
        str(runner),
        "/home/pes/ghidra_projects/shift",
        "shift",
        "SHIFT.exe",
        "out/selected.jsonl",
        "0x00410000",
        "0x00420000",
        "0x00430000",
    ]


def test_builds_exact_runner_command_from_current_root_pose_rank(tmp_path):
    artifact = _rank(
        tmp_path / "root_pose_rank.json",
        ["FUN_004848bc", "0x00480700", "004a8c20"],
        declared_limit=24,
        artifact_format=m.ROOT_POSE_RANK_FORMAT,
    )
    runner = tmp_path / "runner.sh"
    command, selected = m.build_command(
        artifact,
        Path("/home/pes/ghidra_projects/shift"),
        "shift",
        Path("out/root_pose_rank.jsonl"),
        runner=runner,
    )
    assert selected == ["0x004848bc", "0x00480700", "0x004a8c20"]
    assert command[-3:] == selected
    payload, loaded, source_kind = m._load_worklist(artifact, max_functions=64)
    assert payload["format"] == m.ROOT_POSE_RANK_FORMAT
    assert loaded == selected
    assert source_kind == "root-pose rank"


def test_builds_exact_runner_command_from_root_pose_frontier(tmp_path):
    artifact = _root_pose(
        tmp_path / "frontier.json",
        ["FUN_0070db00", "FUN_00481e20", "FUN_0047fa40"],
    )
    runner = tmp_path / "runner.sh"
    command, selected = m.build_command(
        artifact,
        Path("/home/pes/ghidra_projects/shift"),
        "shift",
        Path("out/root_pose.jsonl"),
        runner=runner,
    )
    assert selected == ["0x0070db00", "0x00481e20", "0x0047fa40"]
    assert command[-3:] == selected
    assert command[3] == "SHIFT.exe"


def test_dry_run_does_not_require_ghidra_home_or_execute(tmp_path, monkeypatch, capsys):
    artifact = _root_pose(tmp_path / "frontier.json", ["0x00410000"])
    monkeypatch.delenv("GHIDRA_HOME", raising=False)
    monkeypatch.setattr(m.subprocess, "run", lambda *args, **kwargs: pytest.fail("must not execute"))
    assert m.run(artifact, Path("/project"), "shift", Path("out.jsonl"), dry_run=True) == 0
    text = capsys.readouterr().out
    assert "worklist source: root-pose frontier" in text
    assert "selected function count: 1" in text
    assert "0x00410000" in text


def test_rejects_duplicate_worklist(tmp_path):
    artifact = _rank(tmp_path / "rank.json", ["0x00410000", "FUN_00410000"])
    with pytest.raises(ValueError, match="duplicates"):
        m.build_command(artifact, Path("/project"), "shift", Path("out.jsonl"))


def test_rejects_worklist_above_safety_cap(tmp_path):
    artifact = _rank(tmp_path / "rank.json", [f"0x{0x410000 + i:08x}" for i in range(4)])
    with pytest.raises(ValueError, match="safety cap 3"):
        m.build_command(
            artifact,
            Path("/project"),
            "shift",
            Path("out.jsonl"),
            max_functions=3,
        )


def test_rejects_worklist_above_rank_declared_limit(tmp_path):
    artifact = _rank(
        tmp_path / "rank.json",
        ["0x00410000", "0x00420000"],
        declared_limit=1,
        artifact_format=m.ROOT_POSE_RANK_FORMAT,
    )
    with pytest.raises(ValueError, match="declared export limit"):
        m.build_command(artifact, Path("/project"), "shift", Path("out.jsonl"))


def test_rejects_wrong_retail_identity(tmp_path):
    artifact = _root_pose(tmp_path / "frontier.json", ["0x00410000"], md5="0" * 32)
    with pytest.raises(ValueError, match="retail identity drift"):
        m.build_command(artifact, Path("/project"), "shift", Path("out.jsonl"))


def test_rejects_nonready_artifact(tmp_path):
    artifact = _rank(tmp_path / "rank.json", ["0x00410000"], ready=False)
    with pytest.raises(ValueError, match="not ready"):
        m.build_command(artifact, Path("/project"), "shift", Path("out.jsonl"))


def test_rejects_root_pose_instruction_format_drift(tmp_path):
    artifact = _root_pose(
        tmp_path / "frontier.json",
        ["0x00410000"],
        worklist_format="SHIFT.Other/1",
    )
    with pytest.raises(ValueError, match="instruction format drift"):
        m.build_command(artifact, Path("/project"), "shift", Path("out.jsonl"))
