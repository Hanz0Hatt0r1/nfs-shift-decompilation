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
import json, sys
from pathlib import Path
source=Path(sys.argv[1]); assert source.is_file(); assert sys.argv[2]=='--ghidra-export'; assert Path(sys.argv[3]).is_dir(); assert sys.argv[4]=='--json-out'
Path(sys.argv[5]).write_text(json.dumps({'format':'SHIFT-MEMORY-BACKEND-EVIDENCE/1'})+'\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    for name, env_name, fmt in [
        ("analyze_allocation_diagnostic_slice.py", "BACKEND_ALLOCATION_SLICE_LOG", "SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1"),
        ("analyze_free_diagnostic_slice.py", "BACKEND_FREE_SLICE_LOG", "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1"),
    ]:
        tool = script_dir / name
        tool.write_text(
            f"""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ['{env_name}']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
assert Path(sys.argv[1]).is_file(); assert sys.argv[2]=='--ghidra-export'; assert Path(sys.argv[3]).is_dir(); assert sys.argv[4]=='--json-out'
Path(sys.argv[5]).write_text(json.dumps({{'format':'{fmt}'}})+'\\n', encoding='utf-8')
""",
            encoding="utf-8",
        )

    behavior = script_dir / "analyze_release_byte_behavior.py"
    behavior.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ['BACKEND_RELEASE_BYTE_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
assert Path(sys.argv[1]).is_file(); assert sys.argv[2]=='--json-out'
Path(sys.argv[3]).write_text(json.dumps({'format':'SHIFT-MEMORY-RELEASE-BYTE-BEHAVIOR/1'})+'\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )
    return runner


def test_runner_exports_backend_cluster_then_analyzes_and_slices(tmp_path):
    runner = _prepare_harness(tmp_path)
    output = tmp_path / "out"
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    log = tmp_path / "export_args.txt"
    allocation_slice_log = tmp_path / "allocation_slice_args.txt"
    free_slice_log = tmp_path / "free_slice_args.txt"
    release_byte_log = tmp_path / "release_byte_args.txt"
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["BACKEND_RUNNER_LOG"] = str(log)
    env["BACKEND_ALLOCATION_SLICE_LOG"] = str(allocation_slice_log)
    env["BACKEND_FREE_SLICE_LOG"] = str(free_slice_log)
    env["BACKEND_RELEASE_BYTE_LOG"] = str(release_byte_log)

    result = subprocess.run(
        ["bash", str(runner), "/projects/shift", "shift", "SHIFT.exe", str(ghidra), str(output)],
        env=env, text=True, capture_output=True, check=True,
    )

    args = log.read_text(encoding="utf-8").splitlines()
    assert args[:4] == ["/projects/shift", "shift", "SHIFT.exe", str(output.resolve() / "memory_backend_instructions.jsonl")]
    assert args[4:] == [
        "FUN_00638020", "FUN_006382b0", "FUN_0064f260", "FUN_0064f4c0", "FUN_0064f3a0", "FUN_00657c30",
    ]
    assert allocation_slice_log.read_text(encoding="utf-8").splitlines() == [
        str(output.resolve() / "memory_backend_instructions.jsonl"), "--ghidra-export", str(ghidra.resolve()), "--json-out", str(output.resolve() / "memory_allocation_diagnostic_slice.json"),
    ]
    assert free_slice_log.read_text(encoding="utf-8").splitlines() == [
        str(output.resolve() / "memory_backend_instructions.jsonl"), "--ghidra-export", str(ghidra.resolve()), "--json-out", str(output.resolve() / "memory_free_diagnostic_slice.json"),
    ]
    assert release_byte_log.read_text(encoding="utf-8").splitlines() == [
        str(output.resolve() / "memory_backend_instructions.jsonl"), "--json-out", str(output.resolve() / "memory_release_byte_behavior.json"),
    ]

    assert json.loads((output / "memory_backend_evidence.json").read_text())["format"] == "SHIFT-MEMORY-BACKEND-EVIDENCE/1"
    assert json.loads((output / "memory_allocation_diagnostic_slice.json").read_text())["format"] == "SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1"
    assert json.loads((output / "memory_free_diagnostic_slice.json").read_text())["format"] == "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1"
    assert json.loads((output / "memory_release_byte_behavior.json").read_text())["format"] == "SHIFT-MEMORY-RELEASE-BYTE-BEHAVIOR/1"
    assert "memory release-byte behavior:" in result.stdout


def test_runner_rejects_wrong_argument_count(tmp_path):
    runner = _prepare_harness(tmp_path)
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    result = subprocess.run(["bash", str(runner), "/projects/shift", "shift"], env=env, text=True, capture_output=True)
    assert result.returncode == 2
    assert "Usage:" in result.stderr
