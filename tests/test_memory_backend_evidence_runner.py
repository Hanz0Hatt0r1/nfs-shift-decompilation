import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_memory_backend_evidence.sh"


def _prepare_harness(tmp_path: Path) -> Path:
    script_dir = tmp_path / "tools" / "ghidra"
    script_dir.mkdir(parents=True)
    runner = script_dir / RUNNER.name
    runner.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")

    exporter = script_dir / "run_shift_function_instructions.sh"
    exporter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' \"$@\" > \"${BACKEND_RUNNER_LOG:?}\"
out=$4
mkdir -p -- \"$(dirname -- \"$out\")\"
printf '%s\\n' '{\"format\":\"SHIFT.GhidraFunctionInstructions/1\"}' > \"$out\"
""",
        encoding="utf-8",
    )
    exporter.chmod(0o755)

    analyzer = script_dir / "analyze_memory_backend_evidence.py"
    analyzer.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path
source = Path(sys.argv[1])
assert source.is_file()
assert sys.argv[2] == '--ghidra-export'
assert Path(sys.argv[3]).is_dir()
assert sys.argv[4] == '--json-out'
out = Path(sys.argv[5])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-BACKEND-EVIDENCE/1'}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )
    return runner


def test_runner_exports_exact_backend_cluster_then_analyzes(tmp_path):
    runner = _prepare_harness(tmp_path)
    output = tmp_path / "out"
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    log = tmp_path / "export_args.txt"
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["BACKEND_RUNNER_LOG"] = str(log)

    result = subprocess.run(
        [
            "bash",
            str(runner),
            "/projects/shift",
            "shift",
            "SHIFT.exe",
            str(ghidra),
            str(output),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    args = log.read_text(encoding="utf-8").splitlines()
    assert args[:4] == [
        "/projects/shift",
        "shift",
        "SHIFT.exe",
        str(output.resolve() / "memory_backend_instructions.jsonl"),
    ]
    assert args[4:] == [
        "FUN_00638020",
        "FUN_006382b0",
        "FUN_0064f260",
        "FUN_0064f4c0",
        "FUN_0064f3a0",
        "FUN_00657c30",
    ]

    report = json.loads((output / "memory_backend_evidence.json").read_text(encoding="utf-8"))
    assert report["format"] == "SHIFT-MEMORY-BACKEND-EVIDENCE/1"
    assert "memory backend instruction export:" in result.stdout
    assert "memory backend evidence report:" in result.stdout


def test_runner_rejects_wrong_argument_count(tmp_path):
    runner = _prepare_harness(tmp_path)
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"

    result = subprocess.run(
        ["bash", str(runner), "/projects/shift", "shift"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "Usage:" in result.stderr
