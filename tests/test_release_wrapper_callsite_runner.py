import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "ghidra" / "run_release_wrapper_callsite_evidence.sh"


def _prepare_harness(tmp_path: Path) -> Path:
    tool_dir = tmp_path / "tools" / "ghidra"
    tool_dir.mkdir(parents=True)
    runner = tool_dir / RUNNER.name
    runner.write_text(RUNNER.read_text(encoding="utf-8"), encoding="utf-8")

    inventory = tool_dir / "build_release_wrapper_caller_inventory.py"
    inventory.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ['RELEASE_CALLER_INVENTORY_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
out=Path(sys.argv[sys.argv.index('--json-out')+1])
targets=Path(sys.argv[sys.argv.index('--targets-out')+1])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-RELEASE-WRAPPER-CALLERS/1','selected_caller_count':2,'truncated':False,'callers':[]})+'\\n', encoding='utf-8')
targets.write_text('0x00100000\\n0x00200000\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    exporter = tool_dir / "run_shift_function_instructions.sh"
    exporter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' \"$@\" > \"${RELEASE_CALLER_EXPORT_LOG:?}\"
out=$4
printf '%s\\n' '{\"format\":\"SHIFT.GhidraFunctionInstructions/1\"}' > \"$out\"
""",
        encoding="utf-8",
    )
    exporter.chmod(0o755)

    analyzer = tool_dir / "analyze_release_wrapper_callsites.py"
    analyzer.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ['RELEASE_CALLER_ANALYZER_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
assert Path(sys.argv[1]).is_file(); assert Path(sys.argv[2]).is_file(); assert sys.argv[3]=='--json-out'
Path(sys.argv[4]).write_text(json.dumps({'format':'SHIFT-MEMORY-RELEASE-WRAPPER-CALLSITES/1','callsite_count':2,'resolved_callsite_count':2})+'\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )
    return runner


def test_runner_builds_inventory_exports_callers_and_analyzes(tmp_path):
    runner = _prepare_harness(tmp_path)
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    output = tmp_path / "out"
    inventory_log = tmp_path / "inventory.log"
    export_log = tmp_path / "export.log"
    analyzer_log = tmp_path / "analyzer.log"
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["SHIFT_RELEASE_WRAPPER_MAX_CALLERS"] = "37"
    env["RELEASE_CALLER_INVENTORY_LOG"] = str(inventory_log)
    env["RELEASE_CALLER_EXPORT_LOG"] = str(export_log)
    env["RELEASE_CALLER_ANALYZER_LOG"] = str(analyzer_log)

    result = subprocess.run(
        [
            "bash", str(runner), "/projects/shift", "shift", "SHIFT.exe",
            str(ghidra), str(output),
        ],
        env=env, text=True, capture_output=True, check=True,
    )

    out = output.resolve()
    export = ghidra.resolve()
    assert inventory_log.read_text(encoding="utf-8").splitlines() == [
        str(export), "--max-callers", "37", "--json-out",
        str(out / "release_wrapper_caller_inventory.json"), "--targets-out",
        str(out / "release_wrapper_caller_targets.txt"),
    ]
    assert export_log.read_text(encoding="utf-8").splitlines() == [
        "/projects/shift", "shift", "SHIFT.exe",
        str(out / "release_wrapper_caller_instructions.jsonl"),
        "0x00100000", "0x00200000",
    ]
    assert analyzer_log.read_text(encoding="utf-8").splitlines() == [
        str(out / "release_wrapper_caller_inventory.json"),
        str(out / "release_wrapper_caller_instructions.jsonl"),
        "--json-out", str(out / "release_wrapper_callsite_evidence.json"),
    ]
    report = json.loads((output / "release_wrapper_callsite_evidence.json").read_text())
    assert report["format"] == "SHIFT-MEMORY-RELEASE-WRAPPER-CALLSITES/1"
    assert "release wrapper callsite evidence:" in result.stdout


def test_runner_rejects_invalid_max_callers(tmp_path):
    runner = _prepare_harness(tmp_path)
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["SHIFT_RELEASE_WRAPPER_MAX_CALLERS"] = "0"
    result = subprocess.run(
        ["bash", str(runner), "/p", "shift", "SHIFT.exe", str(ghidra), str(tmp_path / "out")],
        env=env, text=True, capture_output=True,
    )
    assert result.returncode == 2
    assert "positive integer" in result.stderr


def test_runner_rejects_missing_ghidra_export(tmp_path):
    runner = _prepare_harness(tmp_path)
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    result = subprocess.run(
        ["bash", str(runner), "/p", "shift", "SHIFT.exe", str(tmp_path / "missing"), str(tmp_path / "out")],
        env=env, text=True, capture_output=True,
    )
    assert result.returncode == 1
    assert "Ghidra export directory not found" in result.stderr
