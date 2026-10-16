from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "tools/ghidra/adapt_revenginstr_scalar_uses.py"
RUNNER = ROOT / "tools/ghidra/run_shift_scalar_uses.sh"


def _row(format_name: str) -> dict:
    return {
        "format": format_name,
        "program": "SHIFT.exe",
        "target_scalar": "0x374",
        "function_address": "0x00401000",
        "function_name": "FUN_00401000",
        "instruction_address": "0x00401004",
        "mnemonic": "ADD",
        "text": "ADD EAX,0x374",
        "matching_operand_index": 1,
        "matching_operand_text": "0x374",
        "usage_class": "arithmetic",
    }


def test_adapter_changes_only_the_format_field(tmp_path: Path) -> None:
    source = tmp_path / "generic.jsonl"
    destination = tmp_path / "shift.jsonl"
    original = _row("REVENGINSTR.GhidraScalarUses/1")
    source.write_text(json.dumps(original) + "\n", encoding="utf-8")

    subprocess.run(["python3", str(ADAPTER), str(source), str(destination)], check=True)

    adapted = json.loads(destination.read_text(encoding="utf-8"))
    assert adapted == {**original, "format": "SHIFT.GhidraScalarUses/1"}


def test_adapter_rejects_an_unknown_contract(tmp_path: Path) -> None:
    source = tmp_path / "wrong.jsonl"
    destination = tmp_path / "shift.jsonl"
    source.write_text(json.dumps(_row("SHIFT.GhidraScalarUses/1")) + "\n", encoding="utf-8")

    result = subprocess.run(
        ["python3", str(ADAPTER), str(source), str(destination)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "expected REVENGINSTR.GhidraScalarUses/1" in result.stderr


def test_shell_runner_has_valid_bash_syntax() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)


def _fake_headless(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
script_dir = Path(args[args.index('-scriptPath') + 1])
post = args.index('-postScript')
output = Path(args[post + 2])
row = {
    'format': 'SHIFT.GhidraScalarUses/1', 'program': 'SHIFT.exe',
    'target_scalar': args[post + 3], 'function_address': None,
    'function_name': None, 'instruction_address': '0x00401004',
    'mnemonic': 'ADD', 'text': 'ADD EAX,0x374',
    'matching_operand_index': 1, 'matching_operand_text': '0x374',
    'usage_class': 'arithmetic'
}
Path(os.environ['SHIFT_TEST_CAPTURE']).write_text(json.dumps({
    'args': args, 'script_name': args[post + 1],
    'script_files': sorted(p.name for p in script_dir.iterdir())
}))
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(row) + '\\n')
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_runner_prefers_shared_exporter_and_preserves_shift_rows(tmp_path: Path) -> None:
    ghidra_home = tmp_path / "ghidra"
    shared = tmp_path / "revenginstr"
    support = ghidra_home / "support"
    support.mkdir(parents=True)
    (shared / "scripts").mkdir(parents=True)
    (shared / "ghidra").mkdir()
    (shared / "ghidra/ExportGhidraScalarUses.java").write_text("// generic\n", encoding="utf-8")
    shared_runner = shared / "scripts/run_ghidra_scalar_uses.sh"
    shared_runner.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
output = Path(sys.argv[4])
row = {
    'format': 'REVENGINSTR.GhidraScalarUses/1', 'program': 'SHIFT.exe',
    'target_scalar': sys.argv[5], 'function_address': '0x00401000',
    'function_name': 'FUN_00401000', 'instruction_address': '0x00401004',
    'mnemonic': 'ADD', 'text': 'ADD EAX,0x374',
    'matching_operand_index': 1, 'matching_operand_text': '0x374',
    'usage_class': 'arithmetic'
}
Path(os.environ['SHIFT_SHARED_CAPTURE']).write_text(json.dumps(sys.argv[1:]))
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(row) + '\\n')
""",
        encoding="utf-8",
    )
    shared_runner.chmod(shared_runner.stat().st_mode | stat.S_IXUSR)
    _fake_headless(support / "analyzeHeadless")
    capture = tmp_path / "shared-capture.json"
    output = tmp_path / "out/scalar-uses.jsonl"
    env = os.environ.copy()
    env.update(
        GHIDRA_HOME=str(ghidra_home),
        REVENGINSTR_REPO=str(shared),
        SHIFT_SHARED_CAPTURE=str(capture),
        SHIFT_TEST_CAPTURE=str(tmp_path / "fallback-capture.json"),
    )

    subprocess.run(
        ["bash", str(RUNNER), str(tmp_path / "project"), "shift", "SHIFT.exe", str(output), "0x374"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    args = json.loads(capture.read_text(encoding="utf-8"))
    assert args[1:] == ["shift", "SHIFT.exe", args[3], "0x374"]
    adapted = json.loads(output.read_text(encoding="utf-8"))
    assert adapted == {**_row("SHIFT.GhidraScalarUses/1"), "function_address": "0x00401000", "function_name": "FUN_00401000"}
    assert not (tmp_path / "fallback-capture.json").exists()


def test_runner_keeps_local_fallback_when_shared_exporter_is_missing(tmp_path: Path) -> None:
    ghidra_home = tmp_path / "ghidra"
    support = ghidra_home / "support"
    _fake_headless(support / "analyzeHeadless")
    capture = tmp_path / "fallback-capture.json"
    output = tmp_path / "out/scalar-uses.jsonl"
    env = os.environ.copy()
    env.update(
        GHIDRA_HOME=str(ghidra_home),
        REVENGINSTR_REPO=str(tmp_path / "missing-revenginstr"),
        SHIFT_TEST_CAPTURE=str(capture),
    )

    subprocess.run(
        ["bash", str(RUNNER), str(tmp_path / "project"), "shift", "SHIFT.exe", str(output), "0x374"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    observed = json.loads(capture.read_text(encoding="utf-8"))
    assert observed["script_name"] == "ShiftScalarUseExporter.java"
    assert observed["script_files"] == ["ShiftScalarUseExporter.java"]
    assert "-recursive" in observed["args"]
    assert "-readOnly" in observed["args"]
    assert "-noanalysis" in observed["args"]
    row = json.loads(output.read_text(encoding="utf-8"))
    assert row["format"] == "SHIFT.GhidraScalarUses/1"
