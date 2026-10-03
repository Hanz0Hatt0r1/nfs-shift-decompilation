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

    allocation_slicer = script_dir / "analyze_allocation_diagnostic_slice.py"
    allocation_slicer.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
Path(os.environ['BACKEND_ALLOCATION_SLICE_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
source = Path(sys.argv[1])
assert source.is_file()
assert sys.argv[2] == '--ghidra-export'
assert Path(sys.argv[3]).is_dir()
assert sys.argv[4] == '--json-out'
out = Path(sys.argv[5])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1'}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    free_slicer = script_dir / "analyze_free_diagnostic_slice.py"
    free_slicer.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
Path(os.environ['BACKEND_FREE_SLICE_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
source = Path(sys.argv[1])
assert source.is_file()
assert sys.argv[2] == '--ghidra-export'
assert Path(sys.argv[3]).is_dir()
assert sys.argv[4] == '--json-out'
out = Path(sys.argv[5])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1','free_pointer_role_proven':false,'free_pointer_entry_storage':null}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )

    chain = script_dir / "analyze_release_pointer_chain.py"
    chain.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
Path(os.environ['BACKEND_CHAIN_LOG']).write_text('\\n'.join(sys.argv[1:]), encoding='utf-8')
assert Path(sys.argv[1]).is_file()
assert sys.argv[2] == '--free-diagnostic-slice'
assert Path(sys.argv[3]).is_file()
assert sys.argv[4] == '--json-out'
out = Path(sys.argv[5])
out.write_text(json.dumps({'format':'SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1'}) + '\\n', encoding='utf-8')
""",
        encoding="utf-8",
    )
    return runner


def test_runner_exports_backend_cluster_then_builds_semantic_slices_and_chain(tmp_path):
    runner = _prepare_harness(tmp_path)
    output = tmp_path / "out"
    ghidra = tmp_path / "ghidra"
    ghidra.mkdir()
    log = tmp_path / "export_args.txt"
    allocation_slice_log = tmp_path / "allocation_slice_args.txt"
    free_slice_log = tmp_path / "free_slice_args.txt"
    chain_log = tmp_path / "chain_args.txt"
    env = dict(os.environ)
    env["GHIDRA_HOME"] = "/opt/fake-ghidra"
    env["BACKEND_RUNNER_LOG"] = str(log)
    env["BACKEND_ALLOCATION_SLICE_LOG"] = str(allocation_slice_log)
    env["BACKEND_FREE_SLICE_LOG"] = str(free_slice_log)
    env["BACKEND_CHAIN_LOG"] = str(chain_log)

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

    resolved_output = output.resolve()
    args = log.read_text(encoding="utf-8").splitlines()
    assert args[:4] == [
        "/projects/shift",
        "shift",
        "SHIFT.exe",
        str(resolved_output / "memory_backend_instructions.jsonl"),
    ]
    assert args[4:] == [
        "FUN_00638020",
        "FUN_006382b0",
        "FUN_0064f260",
        "FUN_0064f4c0",
        "FUN_0064f3a0",
        "FUN_00657c30",
    ]
    assert allocation_slice_log.read_text(encoding="utf-8").splitlines() == [
        str(resolved_output / "memory_backend_instructions.jsonl"),
        "--ghidra-export",
        str(ghidra.resolve()),
        "--json-out",
        str(resolved_output / "memory_allocation_diagnostic_slice.json"),
    ]
    assert free_slice_log.read_text(encoding="utf-8").splitlines() == [
        str(resolved_output / "memory_backend_instructions.jsonl"),
        "--ghidra-export",
        str(ghidra.resolve()),
        "--json-out",
        str(resolved_output / "memory_free_diagnostic_slice.json"),
    ]
    assert chain_log.read_text(encoding="utf-8").splitlines() == [
        str(resolved_output / "memory_backend_instructions.jsonl"),
        "--free-diagnostic-slice",
        str(resolved_output / "memory_free_diagnostic_slice.json"),
        "--json-out",
        str(resolved_output / "memory_release_pointer_chain.json"),
    ]

    report = json.loads((output / "memory_backend_evidence.json").read_text(encoding="utf-8"))
    assert report["format"] == "SHIFT-MEMORY-BACKEND-EVIDENCE/1"
    allocation_slice = json.loads(
        (output / "memory_allocation_diagnostic_slice.json").read_text(encoding="utf-8")
    )
    assert allocation_slice["format"] == "SHIFT-MEMORY-ALLOCATION-DIAGNOSTIC-SLICE/1"
    free_slice = json.loads((output / "memory_free_diagnostic_slice.json").read_text(encoding="utf-8"))
    assert free_slice["format"] == "SHIFT-MEMORY-FREE-DIAGNOSTIC-SLICE/1"
    release_chain = json.loads((output / "memory_release_pointer_chain.json").read_text(encoding="utf-8"))
    assert release_chain["format"] == "SHIFT-MEMORY-RELEASE-POINTER-CHAIN/1"
    assert "memory backend instruction export:" in result.stdout
    assert "memory backend evidence report:" in result.stdout
    assert "memory allocation diagnostic slice:" in result.stdout
    assert "memory free diagnostic slice:" in result.stdout
    assert "memory release pointer chain:" in result.stdout


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
