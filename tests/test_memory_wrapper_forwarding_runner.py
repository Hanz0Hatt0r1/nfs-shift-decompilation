import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_memory_wrapper_forwarding.sh"


def _prepare_harness(tmp_path: Path) -> Path:
    script_dir = tmp_path / "tools" / "ghidra"
    script_dir.mkdir(parents=True)
    runner = script_dir / RUNNER.name
    runner.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")

    exporter = script_dir / "run_shift_function_instructions.sh"
    exporter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' \"$@\" > \"${WRAPPER_RUNNER_LOG:?}\"
out=$4
mkdir -p -- \"$(dirname -- \"$out\")\"
printf '%s\\n' '{\"format\":\"SHIFT.GhidraFunctionInstructions/1\"}' > \"$out\"
""",
        encoding="utf-8",
    )
    exporter.chmod(0o755)

    analyzer = script_dir / "analyze_memory_wrapper_forwarding_retail.py"
    analyzer.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path
source = Path(sys.argv[1])
assert source.is_file()
assert sys.argv[2] == '--json-out'
out = Path(sys.argv[3])
out.write_text(json.dumps({'format': 'SHIFT-MEMORY-WRAPPER-FORWARDING/1'}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )
    return runner


def test_runner_exports_exact_memory_wrapper_set_then_analyzes(tmp_path):
    runner = _prepare_harness(tmp_path)
    output = tmp_path / "out"
    log = tmp_path / "export_args.txt"
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["WRAPPER_RUNNER_LOG"] = str(log)

    result = subprocess.run(
        [
            "bash",
            str(runner),
            "/projects/shift",
            "shift",
            "SHIFT.exe",
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
        str(output.resolve() / "memory_wrapper_instructions.jsonl"),
    ]
    assert args[4:] == [
        "FUN_008868c0",
        "FUN_008868d0",
        "FUN_00886900",
        "FUN_00886930",
        "FUN_00886950",
    ]

    report_path = output / "memory_wrapper_forwarding.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["format"] == "SHIFT-MEMORY-WRAPPER-FORWARDING/1"
    assert "memory wrapper instruction export:" in result.stdout
    assert "memory wrapper forwarding report:" in result.stdout


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
