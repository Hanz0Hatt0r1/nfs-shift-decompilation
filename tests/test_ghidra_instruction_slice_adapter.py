from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "tools/ghidra/adapt_revenginstr_instruction_slices.py"
RUNNER = ROOT / "tools/ghidra/run_shift_instruction_slices.sh"


def _slice(format_name: str, token: str) -> dict:
    address = token.split(":", 1)[0]
    return {
        "format": format_name,
        "program": "SHIFT.exe",
        "requested": address,
        "start": address,
        "length": 16,
        "exact_instruction_at_start": True,
        "instruction_count": 1,
        "instructions": [_instruction(address)],
    }


def _instruction(address: str) -> dict:
    return {
        "address": address,
        "bytes": "c3",
        "mnemonic": "RET",
        "text": "RET",
        "operands": [],
        "flow_type": "TERMINATOR",
        "fallthrough": None,
        "flows": [],
        "references": [],
        "pcode": [],
    }


def test_adapter_changes_only_format_and_rejects_unknown_contract(tmp_path: Path) -> None:
    source = tmp_path / "generic.jsonl"
    destination = tmp_path / "shift.jsonl"
    generic = _slice("REVENGINSTR.GhidraInstructionSlice/1", "0x00401000:0x10")
    source.write_text(json.dumps(generic) + "\n", encoding="utf-8")
    subprocess.run(["python3", str(ADAPTER), str(source), str(destination)], check=True)
    assert json.loads(destination.read_text()) == {**generic, "format": "SHIFT.GhidraInstructionSlice/1"}

    source.write_text(json.dumps(_slice("wrong", "0x00401000")) + "\n", encoding="utf-8")
    result = subprocess.run(["python3", str(ADAPTER), str(source), str(destination)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "expected REVENGINSTR.GhidraInstructionSlice/1" in result.stderr


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
rows = []
for token in args[post + 3:]:
    address = token.split(':', 1)[0]
    rows.append({'format': 'SHIFT.GhidraInstructionSlice/1', 'program': 'SHIFT.exe',
        'requested': address, 'start': address, 'length': 16,
        'exact_instruction_at_start': True, 'instruction_count': 1,
        'instructions': [{'address': address, 'bytes': 'c3', 'mnemonic': 'RET',
            'text': 'RET', 'operands': [], 'flow_type': 'TERMINATOR',
            'fallthrough': None, 'flows': [], 'references': [], 'pcode': []}]})
Path(os.environ['SHIFT_SLICE_CAPTURE']).write_text(json.dumps({
    'args': args, 'script_name': args[post + 1],
    'script_files': sorted(p.name for p in script_dir.iterdir())
}))
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(''.join(json.dumps(row) + '\\n' for row in rows))
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _fake_shared_runner(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
output = Path(args[3])
rows = []
for token in args[4:]:
    address = token.split(':', 1)[0]
    rows.append({'format': 'REVENGINSTR.GhidraInstructionSlice/1', 'program': 'SHIFT.exe',
        'requested': address, 'start': address, 'length': 16,
        'exact_instruction_at_start': True, 'instruction_count': 1,
        'instructions': [{'address': address, 'bytes': 'c3', 'mnemonic': 'RET',
            'text': 'RET', 'operands': [], 'flow_type': 'TERMINATOR',
            'fallthrough': None, 'flows': [], 'references': [], 'pcode': []}]})
Path(os.environ['SHIFT_SLICE_SHARED_CAPTURE']).write_text(json.dumps(args))
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(''.join(json.dumps(row) + '\\n' for row in rows))
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run(tmp_path: Path, shared: bool) -> tuple[list[dict], dict]:
    ghidra = tmp_path / "ghidra"
    shared_repo = tmp_path / "revenginstr"
    (ghidra / "support").mkdir(parents=True)
    (shared_repo / "ghidra").mkdir(parents=True)
    (shared_repo / "ghidra/ExportGhidraInstructionSlices.java").write_text("// exporter\n")
    capture = tmp_path / "capture.json"
    if shared:
        _fake_shared_runner(shared_repo / "scripts/run_ghidra_instruction_slices.sh")
    _fake_headless(ghidra / "support/analyzeHeadless")
    output = tmp_path / "out/slices.jsonl"
    env = os.environ.copy()
    env.update(
        GHIDRA_HOME=str(ghidra),
        REVENGINSTR_REPO=str(shared_repo if shared else tmp_path / "missing-revenginstr"),
        SHIFT_SLICE_CAPTURE=str(capture),
        SHIFT_SLICE_SHARED_CAPTURE=str(capture),
    )
    targets = ["0x00401000:0x10", "0x00402000:0x20"]
    subprocess.run(
        ["bash", str(RUNNER), str(tmp_path / "project"), "shift", "SHIFT.exe", str(output), *targets],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    rows = [json.loads(line) for line in output.read_text().splitlines() if line.strip()]
    return rows, json.loads(capture.read_text())


def test_runner_prefers_shared_exporter_and_preserves_rows(tmp_path: Path) -> None:
    rows, args = _run(tmp_path, shared=True)
    assert [row["format"] for row in rows] == ["SHIFT.GhidraInstructionSlice/1"] * 2
    assert [row["start"] for row in rows] == ["0x00401000", "0x00402000"]
    assert args[1:3] == ["shift", "SHIFT.exe"]


def test_runner_keeps_local_fallback(tmp_path: Path) -> None:
    rows, observed = _run(tmp_path, shared=False)
    assert [row["format"] for row in rows] == ["SHIFT.GhidraInstructionSlice/1"] * 2
    assert observed["script_name"] == "ShiftInstructionSliceExporter.java"
    assert observed["script_files"] == ["ShiftInstructionSliceExporter.java"]
    assert "-readOnly" in observed["args"] and "-noanalysis" in observed["args"]


def test_runner_shell_syntax() -> None:
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
