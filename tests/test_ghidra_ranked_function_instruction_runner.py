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


def _rank(path: Path, selected, *, ready=True, md5=None, declared_limit=None):
    ranking = {"selected_instruction_export_functions": selected}
    if declared_limit is not None:
        ranking["selected_instruction_export_limit"] = declared_limit
    path.write_text(
        json.dumps(
            {
                "format": m.RANK_FORMAT,
                "ready": ready,
                "retail": {"program": m.PROGRAM, "md5": md5 or m.PE_MD5},
                "ranking": ranking,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_builds_exact_runner_command_from_rank_selected_worklist(tmp_path):
    rank = _rank(
        tmp_path / "rank.json",
        ["FUN_00410000", "0x00420000", "00430000"],
        declared_limit=24,
    )
    runner = tmp_path / "runner.sh"
    command, selected = m.build_command(
        rank,
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


def test_dry_run_does_not_require_ghidra_home_or_execute(tmp_path, monkeypatch, capsys):
    rank = _rank(tmp_path / "rank.json", ["0x00410000"])
    monkeypatch.delenv("GHIDRA_HOME", raising=False)
    monkeypatch.setattr(m.subprocess, "run", lambda *args, **kwargs: pytest.fail("must not execute"))
    assert m.run(rank, Path("/project"), "shift", Path("out.jsonl"), dry_run=True) == 0
    text = capsys.readouterr().out
    assert "rank-selected function count: 1" in text
    assert "0x00410000" in text


def test_rejects_duplicate_worklist(tmp_path):
    rank = _rank(tmp_path / "rank.json", ["0x00410000", "FUN_00410000"])
    with pytest.raises(ValueError, match="duplicates"):
        m.build_command(rank, Path("/project"), "shift", Path("out.jsonl"))


def test_rejects_worklist_above_safety_cap(tmp_path):
    rank = _rank(tmp_path / "rank.json", [f"0x{0x410000 + i:08x}" for i in range(4)])
    with pytest.raises(ValueError, match="safety cap 3"):
        m.build_command(
            rank,
            Path("/project"),
            "shift",
            Path("out.jsonl"),
            max_functions=3,
        )


def test_rejects_worklist_above_rank_declared_limit(tmp_path):
    rank = _rank(
        tmp_path / "rank.json",
        ["0x00410000", "0x00420000"],
        declared_limit=1,
    )
    with pytest.raises(ValueError, match="declared export limit"):
        m.build_command(rank, Path("/project"), "shift", Path("out.jsonl"))


def test_rejects_wrong_retail_identity(tmp_path):
    rank = _rank(tmp_path / "rank.json", ["0x00410000"], md5="0" * 32)
    with pytest.raises(ValueError, match="retail identity drift"):
        m.build_command(rank, Path("/project"), "shift", Path("out.jsonl"))


def test_rejects_nonready_rank(tmp_path):
    rank = _rank(tmp_path / "rank.json", ["0x00410000"], ready=False)
    with pytest.raises(ValueError, match="expected ready"):
        m.build_command(rank, Path("/project"), "shift", Path("out.jsonl"))
